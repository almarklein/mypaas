"""
The Monitor class that performs the aggregation.
"""

import os
import time
import atexit
import hashlib
import weakref
import logging
import datetime
import threading
from queue import Queue, Empty

from ._itemdb import ItemDB


logger = logging.getLogger("mypaas_stats")


# Number of seconds for one aggregation unit. Assume about 1000 B per
# record. Then with chunks of 10 minutes, one year will take about 1000
# * 6 * 24 * 365 / 2**20 = ~ 50 MiB per year.
DEFAULT_STEP = 10 * 60  # 10 minutes
TABLE_NAME = "aggregations"


_monitor_instances = weakref.WeakSet()
_write_queue = Queue(10000)
_helper_thread = None


# When Python exits, flush the current record of all monitors
@atexit.register
def _at_exit():  # pragma: no cover
    for m in _monitor_instances:
        m.flush()


def hashit(value):
    """ Hash any value by applying md5 to the stringified value.
    Returns an integer.
    """
    if isinstance(value, int):
        return abs(value)
    h = hashlib.md5(str(value).encode())
    return abs(int(h.hexdigest()[:14], 16))  # cut at 7 bytes to fit in int64


# Welford's algorithm allows representing (running) measurements without losing
# much precision, and still being able to calculate the mean and std later.
#
# https://github.com/windelbouwman/lognplot/blob/master/lognplot/src/tsdb/sample.rs
# https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_online_algorithm


def _new_num_agg():
    return {"min": 1e20, "max": 0.0, "n": 0, "mean": 0.0, "magic": 0.0}


def std_from_welford(count, mean, magic):
    """ Included for rerefence. The data view must implement this.
    """
    variance = magic / count  # population variance
    # variance = magic / (count - 1)  # sample variance
    return variance ** 0.5


def merge(aggr1, aggr2):
    """ Merge aggr2 into aggr1. The caller is responsible for ensuring that
    aggr1 is a copy to avoid overriding cached data.
    """
    aggr1["time_start"] = min(aggr1["time_start"], aggr2["time_start"])
    aggr1["time_stop"] = max(aggr1["time_stop"], aggr2["time_stop"])
    for key, val2 in aggr2.items():
        if "|" not in key:
            continue
        _, type, *_ = key.split("|")
        if type == "count":
            aggr1[key] = aggr1.get(key, 0) + val2
        elif type == "dcount":
            aggr1[key] = aggr1.get(key, 0) + val2
        elif type == "mcount":
            aggr1[key] = aggr1.get(key, 0) + val2
        elif type == "cat":
            d1 = aggr1.get(key, None)
            if d1 is None:
                aggr1[key] = d1 = {}
            for k, c in val2.items():
                d1[k] = d1.get(k, 0) + c
        elif type == "num":
            d1, d2 = aggr1.get(key, None), aggr2.get(key, None)
            if d1 is None:
                aggr1[key] = d1 = _new_num_agg()
            if d2 is not None:
                d1["min"] = min(d1["min"], d2["min"])
                d1["max"] = max(d1["max"], d2["max"])
                # Gather values
                n1, mean1, magic1 = d1["n"], d1["mean"], d1["magic"]
                n2, mean2, magic2 = d2["n"], d2["mean"], d2["magic"]
                # Welford's merge algorithm
                n = n1 + n2
                mean = (mean1 * n1 + mean2 * n2) / n
                delta = mean2 - mean1
                magic = magic1 + magic2 + (delta * n1) * (delta * n2) / n
                # Store result
                d1["n"], d1["mean"], d1["magic"] = n, mean, magic


class HelperThread(threading.Thread):
    """ Thread that helps the store to periodically safe aggregations to disk.
    """

    def __init__(self):
        super().__init__()
        self.setDaemon(True)

    def run(self):
        t = time.time()
        time1 = t + 1.0
        time10 = t + 10.0

        while True:
            try:
                m, aggr = _write_queue.get(True, 0.1)
                m._write_aggr(aggr)
            except Empty:
                pass
            except Exception:
                time.seep(0.1)

            t = time.time()

            if t > time1:
                time1 = t + 1
                for m in _monitor_instances:
                    try:
                        m._do_each_1_seconds()
                    except Exception:
                        pass

            if t > time10:
                time10 = t + 10
                for m in _monitor_instances:
                    try:
                        m._do_each_10_seconds()
                    except Exception:
                        pass


class Monitor:
    """ Object that aggregates data and stores it into a database at
    regular intervals. Different types of aggregations can be used, see
    ``put()`` for details.

    Any given data is processed fast, and aggregated at once. Data is
    collected in-memory, and is written to a database (in a separate
    thread) when the time-block ends, or when Python (cleanly) exits.
    Each timeblock is step seconds (default 10 minutes).

    The monitor writes its aggregations to the database specified by
    filename. Multiple monitors can safely use the same database, also
    on different threads or processes. In a docker container you can
    also use a database file on the host system (via ``--volume``). On
    a web server, for instance, one database could be used for system
    measurements, one for each (container) process, and one for each
    domain endpoint.
    """

    def __init__(self, filename, *, step=DEFAULT_STEP):
        self._step = int(step)
        # Prepare db
        self._filename = filename
        # Locks
        self._tlocal = threading.local()  # per-thread data
        self._lock_current_aggr = threading.RLock()
        # Init current aggregation
        self._current_aggr = self._create_new_aggr()
        self._current_time_stop = self._current_aggr["time_stop"]
        # Keep track of ids for daily counters
        self._daily_ids = {}  # key -> set of ids, gets cleared each day
        self._monthly_ids = {}
        if os.path.isfile(self._filename):
            db = ItemDB(self._filename)
            try:
                db.ensure("info", "!key")
                daily_ids_info = db.select_one("info", "key == 'daily_ids'")
                day_key = self._current_aggr["time_key"][:10]
                if daily_ids_info and daily_ids_info["time_key"][:10] == day_key:
                    for key in daily_ids_info:
                        if key not in ("key", "time_key"):
                            self._daily_ids[key] = set(daily_ids_info[key])
                monthly_ids_info = db.select_one("info", "key == 'monthly_ids'")
                month_key = self._current_aggr["time_key"][:7]
                if monthly_ids_info and monthly_ids_info["time_key"][:7] == month_key:
                    for key in monthly_ids_info:
                        if key not in ("key", "time_key"):
                            self._monthly_ids[key] = set(monthly_ids_info[key])
            except Exception as err:
                logger.error(
                    f"Failed to restore daily_ids and monthly_ids from db: {err}"
                )
        # Setup our helper thread
        _monitor_instances.add(self)
        global _helper_thread
        if _helper_thread is None:
            _helper_thread = HelperThread()
            _helper_thread.start()

    def _is_locked_in_this_thread(self):
        tlocal = self._tlocal
        try:
            return tlocal.locked is not None
        except AttributeError:
            return False

    def __enter__(self):
        # if we want to be able to use a monitor in different threads.
        if self._is_locked_in_this_thread():
            raise IOError("Already locked by this thread")
        self._tlocal.locked = time.time()
        self._lock_current_aggr.acquire()
        self._maybe_replace_aggr()  # avoid putting in old time-frame
        return self

    def __exit__(self, type, value, traceback):
        self._lock_current_aggr.release()
        self._tlocal.locked = None

    def flush(self):
        """ Flush the current aggregation to disk. Mainly used for testing;
        the monitor automatically flushes to the database when the time
        block ends and when Python exits.
        """
        self._write_aggr(self._next_aggr())

    @property
    def filename(self):
        """ The filename of the database that this Monitor writes to.
        """
        return self._filename

    def _do_each_1_seconds(self):
        """ Gets called by the helper thread about each second.
        Only do stuff that takes a very short time here!
        """
        pass

    def _do_each_10_seconds(self):
        """ Gets called by the helper thread about each 10 seconds.
        Only do stuff that takes a very short time here!
        """
        # For e.g. the SiteMonitor, if no requests come in, we at least
        # flush it
        self._maybe_replace_aggr()

    def _create_new_aggr(self):
        """ Create a fresh aggregation object.
        """
        # Generate a key representing the time corresponding to
        # the start of the current aggregarion block.
        # Format is "yyyy-mm-dd HH:MM:SS". Time is in UTC.
        step = self._step
        block_time = int(time.time() / step) * step
        time_key = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(block_time))
        # Prepare new aggregation object
        new_aggr = {}
        new_aggr["time_key"] = time_key
        new_aggr["time_start"] = int(time.time())  # actual start time
        new_aggr["time_stop"] = block_time + step  # expected stop time
        return new_aggr

    def _next_aggr(self):
        """ Replace the current aggregation object and return the old one.
        """
        # Swap current with a new aggr
        new_aggr = self._create_new_aggr()
        with self._lock_current_aggr:
            cur_aggr = self._current_aggr
            self._current_aggr = new_aggr
            self._current_time_stop = new_aggr["time_stop"]
        # Actual stop time can be earlier
        cur_aggr["time_stop"] = min(cur_aggr["time_stop"], int(time.time()))
        # Return, the helper thread stores it to disk
        return cur_aggr

    def _maybe_replace_aggr(self):
        """ Check whether we should replace the current aggregation
        with a new one.
        """
        if time.time() > self._current_time_stop:
            # Swap out the old aggr and have the helper thread store it
            old_aggr = self._next_aggr()
            _write_queue.put((self, old_aggr))
            # Is this a new day?
            old_day = old_aggr["time_key"][:10]
            new_day = self._current_aggr["time_key"][:10]
            if new_day != old_day:
                self._daily_ids = {}
            # Is this a new month?
            old_month = old_aggr["time_key"][:7]
            new_month = self._current_aggr["time_key"][:7]
            if new_month != old_month:
                self._monthly_ids = {}

    def _write_aggr(self, aggr):
        """ Write the given aggr to disk. Used by the helper thread to write
        aggr's that we put on the _write_queue.
        """
        for key in aggr.keys():
            if not key.startswith("time_"):
                break
        else:
            return  # Nothing in here, return now
        try:
            db = ItemDB(self._filename)
            # Write aggegation
            db.ensure(TABLE_NAME, "!time_key")
            with db:
                x = db.select_one(TABLE_NAME, "time_key == ?", aggr["time_key"])
                if x is not None:
                    merge(x, aggr)
                    aggr = x
                db.put(TABLE_NAME, aggr)
            # Prepare daily ids info
            daily_ids_info = {}
            for key in self._daily_ids.keys():
                daily_ids_info[key] = list(self._daily_ids[key])
            daily_ids_info["key"] = "daily_ids"
            daily_ids_info["time_key"] = self._current_aggr["time_key"][:10]
            # Prepare montly ids info
            monthly_ids_info = {}
            for key in self._monthly_ids.keys():
                monthly_ids_info[key] = list(self._monthly_ids[key])
            monthly_ids_info["key"] = "monthly_ids"
            monthly_ids_info["time_key"] = self._current_aggr["time_key"][:7]
            # Write
            db.ensure("info", "!key")
            with db:
                db.put("info", daily_ids_info)
                db.put("info", monthly_ids_info)
        except Exception as err:
            logger.error("Failed to save aggregations: " + str(err))

    def put(self, key, value=None):
        """ Put a value into the aggregation. Can only be used under
        the context of this object. Returns True if the value was accepted.

        The key should be of the form "<name>|<type>|<unit>". The unit
        is optional, recognized units include "iB", "s", "%". These
        are handled apropriately.

        The type can be:

        * count: Simply count occurances. Aggregating is summing. The
          value is added to the count, but can also be omitted (default 1).
        * dcount: Count stuff daily. Aggregating is summing, the sum
          over a day is all that really counts. Values are only accepted if
          the given value (a hashable object) has not been seen this (UTC) day.
        * mcount: Same ast dcount, but per month, e.g. unique site visitors.
        * cat: a categorical value. Aggregating is summing the items.
          The value is a string. If ir contains " - " then the left part is
          considered a group to be used while sorting the values for display.
        * num: a numeric value. Aggregating tracks min, max, mean and std.
        """
        # todo: add wcount
        if not self._is_locked_in_this_thread():
            raise IOError("Can only put() under a context.")
        # Pare input
        parts = key.split("|")
        if len(parts) == 2:
            name, type = parts
            unit = ""
        elif len(parts) == 3:
            name, type, unit = parts
        else:
            raise ValueError(
                f"put() key needs name|type or name|type|unit, not {key!r}"
            )
        # Triage over type
        try:
            if type == "count":
                value = 1 if value is None else int(value)
                self._current_aggr[key] = self._current_aggr.get(key, 0) + value
                return True
            elif type == "dcount":
                if value is not None:
                    value = hashit(value)
                    ids = self._daily_ids.setdefault(key, set())
                    if value not in ids:
                        ids.add(value)
                        self._current_aggr[key] = self._current_aggr.get(key, 0) + 1
                        return True
            elif type == "mcount":
                if value is not None:
                    value = hashit(value)
                    ids = self._monthly_ids.setdefault(key, set())
                    if value not in ids:
                        ids.add(value)
                        self._current_aggr[key] = self._current_aggr.get(key, 0) + 1
                        return True
            elif type == "cat":
                if value is not None:
                    value = str(value)
                    if value:
                        d = self._current_aggr.setdefault(key, {})
                        d[value] = d.get(value, 0) + 1
                        return True
            elif type == "num":
                if value is not None:
                    value = float(value)
                    d = self._current_aggr.get(key, None)
                    if d is None:
                        d = _new_num_agg()
                        self._current_aggr[key] = d
                    d["min"] = min(value, d["min"])
                    d["max"] = max(value, d["max"])
                    n1, mean1, magic1 = d["n"], d["mean"], d["magic"]
                    # -- Native implementation, implementing merge for n = 1.
                    # n = n1 + 1
                    # mean = (mean1 * n1 + value) / n
                    # delta = value - mean1
                    # magic = magic1 + (delta * n1) * delta / n
                    # -- Welford online algorithm. Shortcuts -> higher precision
                    n = n1 + 1
                    mean = mean1 + (value - mean1) / n
                    magic = magic1 + (value - mean1) * (value - mean)
                    # Store
                    d["n"], d["mean"], d["magic"] = n, mean, magic
                    return True
            else:
                raise NameError("Unknown aggregation type")
        except Exception as err:
            logger.error(f"Failed to put {type} aggregation {key}: {err}")

    def get_current_aggr(self):
        """ Get (a copy of) the current aggregation record.
        """
        with self._lock_current_aggr:
            return self._current_aggr.copy()

    def get_aggregations(self, first_day, last_day):
        """ Get aggregations between two given days (inclusive).
        If the last day is today, also include the current aggregation.
        """
        assert isinstance(first_day, datetime.date)
        assert isinstance(last_day, datetime.date)
        today = time.gmtime()  # UTC
        today = datetime.date(today.tm_year, today.tm_mon, today.tm_mday)
        one_day = datetime.timedelta(days=1)

        data = []

        db = ItemDB(self.filename)
        try:
            data = db.select(
                TABLE_NAME,
                "time_key >= ? AND time_key < ?",
                first_day.strftime("%Y-%m-%d"),
                (last_day + one_day).strftime("%Y-%m-%d"),
            )
        except KeyError:
            pass  # Invalid table name

        if last_day == today:
            data.append(self.get_current_aggr())

        return data
