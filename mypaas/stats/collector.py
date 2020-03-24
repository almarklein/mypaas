"""
The logic for collecting stats, feeding them into monitor objects, and
querying these data.
"""

import os
import time
import json
import socket
import logging
import datetime
import threading

import psutil

from .monitor import Monitor, merge, _monitor_instances, TABLE_NAME, logger
from ._itemdb import ItemDB


db_dir = os.path.expanduser("~/_stats")
os.makedirs(db_dir, exist_ok=True)


class StatsCollector:
    """ Central object that collects data, distributing it into different
    monitor objects (which are each backed by a sqlite db).
    """

    def __init__(self):
        self._monitors = {}
        self._available_categories = set()
        self._last_values = {}

        for fname in os.listdir(db_dir):
            if fname.endswith(".db"):
                self._available_categories.add(fname[:-3])

    def _get_db_name(self, category):
        return os.path.join(db_dir, category + ".db")

    def _get_monitor(self, category):
        try:
            return self._monitors[category]
        except KeyError:
            monitor = Monitor(self._get_db_name(category))
            self._monitors[category] = monitor
            self._available_categories.add(category)
            return monitor

    def put(self, category, **kwargs):
        # todo: revise how keys in kwargs should be
        monitor = self._get_monitor(category)
        with monitor:
            for key, value in kwargs.items():
                self._last_values[category + "/" + key] = value
                monitor.put(key, value)

    def get_category_list(self):
        x = sorted(self._available_categories.difference(["system"]))
        return ("system",) + tuple(x)

    def get_latest_value(self, category, key):
        return self._last_values.get(category + "/" + key, None)

    def get_data(self, categories, ndays, daysago):
        """ Get aggegation data from ndays1 ago to ndays2 ago. The
        result is a dict, in which the keys are the categores, and each
        value is a list of the aggregations in the corresponding
        category. The aggegations are combined (aggegregated further)
        if needed to keep the returned list to a reasonable size.

        Note that this call performs sync queries to a database, so you
        might want to asyncify the calling of this method.
        """
        assert isinstance(categories, list)

        # Get range of days to collect
        today = time.gmtime()  # UTC
        today = datetime.date(today.tm_year, today.tm_mon, today.tm_mday)
        one_day = datetime.timedelta(days=1)
        final_day = today - one_day * daysago
        first_day = today - one_day * (daysago + ndays - 1)

        t1 = int(time.mktime(first_day.timetuple()))
        t2 = int(time.mktime((final_day + one_day).timetuple()))

        # Collect all data
        # todo: Aggregate as we iterate over data? (ItemDB would need select_iter())
        data_per_db = {}

        for category in categories:

            data = []

            # Load data from db
            filename = self._get_db_name(category)
            if os.path.isfile(filename):
                db = ItemDB(filename)
                try:
                    data = db.select(
                        TABLE_NAME,
                        "time_key >= ? AND time_key < ?",
                        first_day.strftime("%Y-%m-%d"),
                        (final_day + one_day).strftime("%Y-%m-%d"),
                    )
                except KeyError:
                    pass  # Invalid table name

            # Load data from running monitors
            if final_day == today:
                for monitor in _monitor_instances:
                    if monitor.filename == filename:
                        data.append(monitor.get_current_aggr())

            # Determine level of aggregation: none, hour, day, month
            nchars = 20
            keys = {aggr["time_key"] for aggr in data}
            for n in [16, 15, 13, 10, 7]:  # min, 10 min, hour, day, month
                if len(keys) > 150:
                    nchars = n
                    keys = {key[:nchars] for key in keys}

            # Merge aggr's that have the same key.
            data2 = [{"time_key": "x"}]
            for aggr in data:
                key = aggr["time_key"][:nchars]
                if key == data2[-1]["time_key"]:
                    merge(data2[-1], aggr)
                else:
                    aggr = aggr.copy()
                    aggr["time_key"] = key
                    data2.append(aggr)

            # Put a stub aggregation at the beginning and end so that all figures
            # have the same time range.
            if len(data2) == 1:
                data = []
            else:
                data = data2
                x = {"time_key": "x"}
                x["time_start"] = x["time_stop"] = min(t1, data[1]["time_start"])
                data[0] = x.copy()
                x["time_start"] = x["time_stop"] = max(t2, data[-1]["time_stop"])
                data.append(x.copy())

            # Store
            name = os.path.basename(filename)
            if name.endswith(".db"):
                name = name[:-3]
            data_per_db[name] = data

        return data_per_db


class UdpStatsReceiver(threading.Thread):
    """ Thread that receives stats from UDP, send by other processes.
    Accepts (most of) statsd format, and a wee bit influxDB because that's
    what Traefik sends us.
    """

    def __init__(self):
        super().__init__()
        self.setDaemon(True)  # don't let this thread prevent shutdown

    def run(self):
        port = 8125
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", port))

        while True:
            data, addr = s.recvfrom(4096)
            try:
                self._process_data(data.decode(errors="ignore"))
            except Exception:
                pass

    def _process_data(self, text):
        """ Parse incoming data and put it into the collector.
        """
        if text.startswith("traefik"):
            category, stats = self._process_data_traefik(text)
        else:
            stats = json.loads(text)
            category = stats.pop("category", "other")

        collector.put(category, **stats)

    def _process_data_traefik(self, text):
        """ Parsers a tiny and Traefik-specific set of influxDB.
        """
        stats = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("traefik.service.requests.total"):
                _, sep, post = line.partition(" count=")
                if sep:
                    try:
                        stats["count requests"] = int(post.split(" ")[0])
                    except ValueError:
                        pass
            elif line.startswith("traefik.service.connections.open"):
                _, sep, post = line.partition(" value=")
                if sep:
                    try:
                        stats["num open-connections"] = int(post.split(" ")[0])
                    except ValueError:
                        pass
            elif line.startswith("traefik.service.request.duration"):
                _, sep, post = line.partition(" p50=")
                if sep:
                    try:
                        stats["num duration s"] = float(
                            post.split(" ")[0].split(",")[0]
                        )
                    except ValueError:
                        pass
            else:
                pass  # drop it
        return "system", stats


class SystemStatsProducer(threading.Thread):
    """ Thead that produces system measurements.
    Currently measuring CPU, RAM and ssd.
    """

    def __init__(self):
        super().__init__()
        self.setDaemon(True)

    def run(self):
        t = time.time()
        time1 = int(t)
        time10 = int(t / 10)

        while True:
            time.sleep(0.05)
            t = time.time()
            t1 = int(t)
            t10 = int(t / 10)

            if t1 > time1:
                time1 = t1
                try:
                    self._do_each_1_seconds()
                except Exception:
                    pass

            if t10 > time10:
                time10 = t10
                try:
                    self._do_each_10_seconds()
                except Exception:
                    pass

    def _do_each_1_seconds(self):
        try:
            # Measure for system (host system when using Docker)
            syscpu = psutil.cpu_percent()  # avg since last call, over all cpus
            sysmem = psutil.virtual_memory().used
            # Put in store

            collector.put(
                "system", num_cpu_perc=max(syscpu, 0.01), num_sys_mem_iB=sysmem
            )
        except Exception as err:
            logger.error("Failed to put system measurements: " + str(err))

    def _do_each_10_seconds(self):
        try:
            # Measure for system (host system when using Docker)
            disk = psutil.disk_usage("/").used
            collector.put("system", num_disk_iB=disk)
        except Exception as err:
            logger.error("Failed to put system measurements: " + str(err))


# Boot it all up

collector = StatsCollector()

udp_stats_receiver = UdpStatsReceiver()
udp_stats_receiver.start()

system_stats_produder = SystemStatsProducer()
system_stats_produder.start()
