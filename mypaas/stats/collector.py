import os
import time
import datetime

from .monitor import Monitor, merge


class StatsCollector:
    """ Central object that collects data, distributing it into different
    monitor objects (which are each backed by an sqlite db).
    """

    def __init__(self, db_dir):
        os.makedirs(db_dir, exist_ok=True)
        self._db_dir = db_dir
        self._monitors = {}
        self._available_groups = set()
        self._last_values = {}

        for fname in os.listdir(self._db_dir):
            if fname.endswith(".db"):
                self._available_groups.add(fname[:-3])

    def _get_db_name(self, group):
        return os.path.join(self._db_dir, group + ".db")

    def _get_monitor(self, group):
        try:
            return self._monitors[group]
        except KeyError:
            monitor = Monitor(self._get_db_name(group))
            self._monitors[group] = monitor
            self._available_groups.add(group)
            return monitor

    def put(self, group, stats):
        monitor = self._get_monitor(group)
        t = time.time()
        with monitor:
            for key, value in stats.items():
                self._last_values[group + ">" + key] = t, value
                monitor.put(key, value)

    def put_one(self, group, key, value):
        """ Put a single value into the groups monitor, and return
        whether the value was accepted.
        """
        monitor = self._get_monitor(group)
        self._last_values[group + ">" + key] = time.time(), value
        with monitor:
            return monitor.put(key, value)

    def get_groups(self):
        """ Get a tuple of groups known to this collector.
        """
        come_first = {"system", "stats", "traefik", "daemon"}
        come_last = {"other"}
        groups = self._available_groups.copy()
        groups1 = groups.intersection(come_first)
        groups3 = groups.intersection(come_last)
        groups2 = groups.difference(come_first | come_last)
        groups1 = tuple(sorted(groups1, key=lambda x: x.replace("sys", "_sys")))
        return groups1 + tuple(sorted(groups2)) + tuple(sorted(groups3))

    def get_latest_value(self, group, key):
        t, value = self._last_values.get(group + ">" + key, (0, None))
        etime = 5 if key == "cpu|num|%" else 60
        if time.time() - t < etime:
            return value
        else:
            return None

    def get_data(self, groups, ndays, daysago):
        """ Get aggegation data from ndays ago to daysago. The
        result is a dict, in which the keys are the categores, and each
        value is a list of the aggregations in the corresponding
        group. The aggegations are combined (aggegregated further)
        if needed to keep the returned list to a reasonable size.

        Note that this call performs sync queries to a database, so you
        might want to asyncify the calling of this method.
        """
        assert isinstance(groups, list)

        # Get range of days to collect
        today = time.gmtime()  # UTC
        today = datetime.date(today.tm_year, today.tm_mon, today.tm_mday)
        one_day = datetime.timedelta(days=1)
        final_day = today - one_day * daysago
        first_day = today - one_day * (daysago + ndays - 1)

        t1 = int(time.mktime(first_day.timetuple()))
        t2 = int(time.mktime((final_day + one_day).timetuple()))

        # Collect all data
        data_per_group = {}

        for group in groups:

            # Get 10 min aggregations from monitor
            monitor = self._get_monitor(group)
            data = monitor.get_aggregations(first_day, final_day)

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

            data_per_group[group] = data

        return data_per_group
