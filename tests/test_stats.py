import os
import gc
import time
import json
import random
import tempfile
import statistics as st

from testutils import run_tests
import asgineer.testutils

import mypaas.stats.collector
from mypaas.stats import Monitor
from mypaas.stats.collector import StatsCollector
from mypaas.stats.monitor import _monitor_instances, std_from_welford

from pytest import raises


db_dir = os.path.join(tempfile.gettempdir(), "stat_db_dir")
os.makedirs(db_dir, exist_ok=True)
group = "mypaastestgroup"
filename = os.path.join(db_dir, group + ".db")


def clean_db():
    gc.collect()
    _monitor_instances.clear()
    for fname in os.listdir(db_dir):
        try:
            os.remove(os.path.join(db_dir, fname))
        except Exception:
            pass


# %% Test some first things


def test_monitor_cleans_up():
    clean_db()

    m = Monitor(filename)
    assert len(_monitor_instances) == 1

    del m
    gc.collect()
    assert len(_monitor_instances) == 0


def test_collector_cleans_up():
    clean_db()

    c = StatsCollector(db_dir)
    assert len(_monitor_instances) == 0

    c.put(group, {"foo|num": 1})
    assert len(_monitor_instances) == 1

    del c
    gc.collect()
    assert len(_monitor_instances) == 0


# %% Monitor


def test_monitor_basics():
    clean_db()

    m = Monitor(filename)

    # Need context
    with raises(IOError):
        m.put("foo|count")

    # Ok to use silly types, it is not accepted and an error is logged
    with m:
        assert not m.put("foo|countx")

    # Correct
    with m:
        assert m.put("foo|count")


def test_monitor_no_writes_when_empty():
    clean_db()

    m = Monitor(filename)

    m.flush()
    assert not os.path.isfile(filename)

    with m:
        pass

    m.flush()
    assert not os.path.isfile(filename)

    with m:
        m.put("x|count")

    m.flush()
    assert os.path.isfile(filename)


def test_monitor_welford():
    """Test that numeric measuremens indeed produce correct mean and std.
    The monitor uses the Welford algorithm, we thus test whether we
    implemented it correctly.
    """
    clean_db()

    _m = random.random() + 2
    numbers1 = [random.random() * 4 + _m for _ in range(42)]
    numbers2 = [random.random() * 4 + _m for _ in range(19)]
    numbers3 = numbers1 + numbers2

    m1 = Monitor(filename + "x1.db")
    m2 = Monitor(filename + "x2.db")
    m3 = Monitor(filename + "x3.db")

    for m in (m1, m2, m3):
        m._do_each_10_seconds = lambda: None  # Prevent flushing the aggregations

    with m1:
        for n in numbers1:
            m1.put("foo|num", n)
    with m2:
        for n in numbers2:
            m2.put("foo|num", n)
    with m3:
        for n in numbers3:
            m3.put("foo|num", n)

    agg1 = m1.get_current_aggr()
    agg2 = m2.get_current_aggr()
    agg3 = m3.get_current_aggr()

    agg4 = agg1.copy()
    agg4["foo|num"] = agg1["foo|num"].copy()
    mypaas.stats.monitor.merge(agg4, agg2)

    a1, a2, a3, a4 = agg1["foo|num"], agg2["foo|num"], agg3["foo|num"], agg4["foo|num"]

    assert a1["n"] == len(numbers1)
    assert abs(a1["mean"] - st.mean(numbers1)) < 0.0001
    assert abs((a1["magic"] / a1["n"]) ** 0.5 - st.pstdev(numbers1)) < 0.0001

    assert a2["n"] == len(numbers2)
    assert abs(a2["mean"] - st.mean(numbers2)) < 0.0001
    assert abs((a2["magic"] / a2["n"]) ** 0.5 - st.pstdev(numbers2)) < 0.0001

    assert a3["n"] == len(numbers3)
    assert abs(a3["mean"] - st.mean(numbers3)) < 0.0001
    assert abs((a3["magic"] / a3["n"]) ** 0.5 - st.pstdev(numbers3)) < 0.0001

    assert a4["n"] == len(numbers3)
    assert abs(a4["mean"] - st.mean(numbers3)) < 0.0001
    assert abs((a4["magic"] / a4["n"]) ** 0.5 - st.pstdev(numbers3)) < 0.0001

    assert (
        abs(std_from_welford(a4["n"], a4["mean"], a4["magic"]) - st.pstdev(numbers3))
        < 0.0001
    )


def test_monitor_merge_count():
    """Test that mering counts goes well"""
    clean_db()

    numbers1 = [random.randint(1, 5) for _ in range(42)]
    numbers2 = [random.randint(1, 5) for _ in range(19)]
    numbers3 = numbers1 + numbers2

    m1 = Monitor(filename + "x1.db")
    m2 = Monitor(filename + "x2.db")
    m3 = Monitor(filename + "x3.db")

    for m in (m1, m2, m3):
        m._do_each_10_seconds = lambda: None  # Prevent flushing the aggregations

    with m1:
        for n in numbers1:
            m1.put("foo|count", n)

    with m2:
        for n in numbers2:
            m2.put("foo|count", n)
    with m3:
        for n in numbers3:
            m3.put("foo|count", n)

    agg1 = m1.get_current_aggr()
    agg2 = m2.get_current_aggr()
    agg3 = m3.get_current_aggr()

    agg4 = agg1.copy()
    # agg4["foo|count"] = agg1["foo|count"].copy()
    mypaas.stats.monitor.merge(agg4, agg2)

    a1, a2, a3, a4 = (
        agg1["foo|count"],
        agg2["foo|count"],
        agg3["foo|count"],
        agg4["foo|count"],
    )

    assert a1 == sum(numbers1)
    assert a2 == sum(numbers2)
    assert a3 == sum(numbers3)
    assert a4 == sum(numbers3)


def test_monitor_merge_cat():
    """Test that merging counts goes well"""
    clean_db()

    # Generate two lists with random numbers from [1, 2, 3, 4, 5]
    numbers1 = [random.randint(1, 5) for _ in range(42)]
    numbers2 = [random.randint(1, 5) for _ in range(19)]
    # Make sure that each number is present at least once (makes processing easier)
    for i in range(1, 6):
        if i not in numbers1:
            numbers1.append(i)
        if i not in numbers2:
            numbers2.append(i)
    # Create a third list that combines the two lists
    numbers3 = numbers1 + numbers2

    m1 = Monitor(filename + "x1.db")
    m2 = Monitor(filename + "x2.db")
    m3 = Monitor(filename + "x3.db")

    for m in (m1, m2, m3):
        m._do_each_10_seconds = lambda: None  # Prevent flushing the aggregations

    with m1:
        for n in numbers1:
            m1.put("foo|cat", n)

    with m2:
        for n in numbers2:
            m2.put("foo|cat", n)
    with m3:
        for n in numbers3:
            m3.put("foo|cat", n)

    agg1 = m1.get_current_aggr()
    agg2 = m2.get_current_aggr()
    agg3 = m3.get_current_aggr()

    agg4 = agg1.copy()
    agg4["foo|cat"] = agg1["foo|cat"].copy()
    mypaas.stats.monitor.merge(agg4, agg2)

    a1, a2, a3, a4 = agg1["foo|cat"], agg2["foo|cat"], agg3["foo|cat"], agg4["foo|cat"]

    assert a1 == {str(i): numbers1.count(i) for i in range(1, 6)}
    assert a2 == {str(i): numbers2.count(i) for i in range(1, 6)}
    assert a3 == {str(i): numbers3.count(i) for i in range(1, 6)}
    assert a4 == {str(i): numbers3.count(i) for i in range(1, 6)}


# %% Receiver


def test_udp_receiver():
    class StubCollector:
        def __init__(self):
            self.data = []

        def put(self, group, stats):
            self.data.append((group, stats))

    collector = StubCollector()
    receiver = mypaas.stats.UdpStatsReceiver(collector)

    # We don't start the thread, so we don't use UDP, but we fo test its logic
    # socket.sendto(f"hello {d}".encode(), ("127.0.0.1", 8125))

    # We support influxDB subset for messages from Trafik
    receiver.process_data("traefik.service.requests.total count=32 ")
    receiver.process_data("traefik.service.connections.open value=4 ")
    receiver.process_data("traefik.service.request.duration p50=0.007,")

    # We also support statsdb
    receiver.process_data("foo:2|c\nbar:3|ms")

    # But we prefer our own little json format"
    receiver.process_data('{"group": "spam", "foo|num": 3, "bar|count": 2}')

    data = collector.data
    assert len(data) == 5

    assert data[0] == ("traefik", {"requests|count": 32})
    assert data[1] == ("traefik", {"open connections|num": 4})
    assert data[2] == ("traefik", {"duration|num|s": 0.007})

    assert data[3] == ("other", {"foo|count": 2, "bar|num|s": 0.003})

    assert data[4] == ("spam", {"foo|num": 3, "bar|count": 2})


def test_receiver_process_speed():
    # Some notes:
    # * We don't actually count the overhead of UDP, though that should be small.
    # * We also measure the time it costs to generate the data.
    # * Numerics are probably the most expensive.

    clean_db()

    is_pytest = "PYTEST_CURRENT_TEST" in os.environ
    collector = StatsCollector(db_dir)
    receiver = mypaas.stats.UdpStatsReceiver(collector)

    t0 = time.perf_counter()
    n = 1000 if is_pytest else 10000
    for i in range(n):
        payload = {
            "group": group,
            "foo|count": 1,
            "bar|dcount": random.randint(0, 99999),
            "spam|mcount": random.randint(0, 99999),
            "eggs|cat": "".join(random.choice("opqxyz") for i in range(3)),
            "meh|num": random.random() + 1,
            "bla|num|iB": random.random() * 100 + 10000,
            # "shazbot|num|iB": random.random() * 100 + 10000,
        }
        receiver.process_data(json.dumps(payload))

    t1 = time.perf_counter()
    time_per_iter = (t1 - t0) / n
    stats_per_second = n / (t1 - t0)
    print(
        f"{n}: {time_per_iter * 1000000:0.0f}us per stat, or {stats_per_second:0.0f} stats per second."
    )
    if is_pytest:
        assert stats_per_second > 1000  # probably slow due to tracing
    else:
        assert stats_per_second > 10000


# %% Collector


def test_collector():
    clean_db()

    collector = StatsCollector(db_dir)
    assert collector.get_groups() == ()

    collector.put("bb", {"foo|num": 3})
    collector.put("zz", {"foo|num": 3})
    collector.put("aa", {"foo|num": 3})
    collector.put("system", {"foo|num": 3})

    assert collector.get_latest_value("bb", "foo|num") == 3
    collector.put("bb", {"foo|num": 5})
    assert collector.get_latest_value("bb", "foo|num") == 5

    assert collector.put_one("bb", "foo|dcount", 3)
    assert not collector.put_one("bb", "foo|dcount", 3)
    assert collector.put_one("bb", "foo|dcount", "foobar")
    assert not collector.put_one("bb", "foo|dcount", "foobar")

    # "system" comes first, then alphabetically
    assert collector.get_groups() == ("system", "aa", "bb", "zz")

    # Stop it
    for m in _monitor_instances:
        m.flush()
    del collector
    gc.collect()
    assert len(_monitor_instances) <= 1

    # The files are still there, and the collector picks them up
    collector = StatsCollector(db_dir)
    assert collector.get_groups() == ("system", "aa", "bb", "zz")


def test_collector_aggr():
    clean_db()

    collector = StatsCollector(db_dir)
    assert collector.get_groups() == ()

    # Put one count via the collector
    collector.put("aa", {"foo|count": 1})

    # Get assocuated monitor and put two more in
    monitor = collector._monitors["aa"]
    collector.put("aa", {"foo|count": 2})

    # Now we should have three
    units = collector.get_data(["aa"], 1, 0)["aa"]
    foo_sum = sum(unit.get("foo|count", 0) for unit in units)
    foo_max = max(unit.get("foo|count", 0) for unit in units)
    foo_num = sum("foo|count" in unit for unit in units)
    assert foo_sum == 3
    assert foo_max == 3
    assert foo_num == 1

    # --

    # Artificially move current aggregation backwards in time
    earlier = time.time() - 30 * 60  # 30 minutes ago
    time_key = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(earlier))
    monitor._current_aggr["time_key"] = time_key
    monitor._current_aggr["time_start"] = earlier
    monitor._current_aggr["time_stop"] = monitor._current_time_stop = earlier + 60

    # Push one 2 more counts
    collector.put("aa", {"foo|count": 2})

    # Now we should have 5, in two bins
    time.sleep(0.1)  # Give helper thread time to process
    units = collector.get_data(["aa"], 1, 0)["aa"]
    foo_sum = sum(unit.get("foo|count", 0) for unit in units)
    foo_max = max(unit.get("foo|count", 0) for unit in units)
    foo_num = sum("foo|count" in unit for unit in units)
    assert foo_sum == 5
    assert foo_max == 3
    assert foo_num == 2

    # And if we look at this on a higher scale, the bins should merge
    units = collector.get_data(["aa"], 14, 0)["aa"]
    foo_sum = sum(unit.get("foo|count", 0) for unit in units)
    foo_max = max(unit.get("foo|count", 0) for unit in units)
    foo_num = sum("foo|count" in unit for unit in units)
    assert foo_sum == 5
    assert foo_max == 5
    assert foo_num == 1


# %% Server


def test_server():
    clean_db()

    collector = StatsCollector(db_dir)
    collector.put("aaa", {"foo|num": 3})
    collector.put("bbb", {"foo|num": 3})

    async def main_handler(request):
        return await mypaas.stats.stats_handler(request, collector)

    with asgineer.testutils.MockTestServer(main_handler) as server:

        # Root page
        r = server.request("GET", "/")
        assert r.status == 200
        assert r.body.startswith(b"<!DOCTYPE html>")
        assert b"aaa" in r.body
        assert b"bbb" in r.body
        assert b"ccc" not in r.body

        # Now add a measurement in a new group, and see that its in there
        collector.put("ccc", {"foo|num": 3})
        r = server.request("GET", "/")
        assert b"aaa" in r.body
        assert b"bbb" in r.body
        assert b"ccc" in r.body

        # Empty stats redirects
        r = server.request("GET", "/stats")
        assert r.status == 302

        # Other stats get info
        r = server.request("GET", "/stats?groups=aa,bb")
        assert r.status == 200

        # Style sheet is separate
        r = server.request("GET", "/style.css")
        assert r.status == 200
        assert b"padding:" in r.body

        # Invalid
        assert server.request("PUT", "/").status == 405
        assert server.request("GET", "/no_valid_page").status == 404


if __name__ == "__main__":
    run_tests(globals())
