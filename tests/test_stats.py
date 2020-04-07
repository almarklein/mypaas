import os
import gc
import time
import socket
import random
import tempfile
import statistics as st

from testutils import run_tests
import asgineer.testutils

import mypaas.stats.collector
from mypaas.stats import Monitor
from mypaas.stats.collector import StatsCollector
from mypaas.stats.monitor import _monitor_instances

from pytest import raises


db_dir = os.path.join(tempfile.gettempdir(), "stat_db_dir")
os.makedirs(db_dir, exist_ok=True)
category = "mypaastestcategory"
filename = os.path.join(db_dir, category + ".db")


def clean_db():
    gc.collect()
    _monitor_instances.clear()
    for fname in os.listdir(db_dir):
        try:
            os.remove(os.path.join(db_dir, fname))
        except Exception:
            pass


## Test some first things


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

    c.put(category, num_foo=0)
    assert len(_monitor_instances) == 1

    del c
    gc.collect()
    assert len(_monitor_instances) == 0


## Monitor


def test_monitor_basics():
    clean_db()

    m = Monitor(filename)

    # Need context
    with raises(IOError):
        m.put("count foo")

    # Ok to use silly types, it is not accepted and an error is logged
    with m:
        assert not m.put("countx foo")

    # Correct
    with m:
        assert m.put("count foo")


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
        m.put("count x")

    m.flush()
    assert os.path.isfile(filename)


def test_monitor_welford():
    """ Test that numeric measuremens indeed produce correct mean and std.
    The monitor uses the Welford algorithm, we thus test whether we
    implemented it correctly.
    """

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
            m1.put("num foo", n)
    with m2:
        for n in numbers2:
            m2.put("num foo", n)
    with m3:
        for n in numbers3:
            m3.put("num foo", n)

    agg1 = m1.get_current_aggr()
    agg2 = m2.get_current_aggr()
    agg3 = m3.get_current_aggr()

    agg4 = agg1.copy()
    agg4["num_foo"] = agg1["num_foo"].copy()
    mypaas.stats.monitor.merge(agg4, agg2)

    a1, a2, a3, a4 = agg1["num_foo"], agg2["num_foo"], agg3["num_foo"], agg4["num_foo"]

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


## Receiver


def test_udp_receiver():
    class StubCollector:
        def __init__(self):
            self.data = []

        def put(self, category, **kwargs):
            self.data.append((category, kwargs))

    collector = StubCollector()
    receiver = mypaas.stats.UdpStatsReceiver(collector)

    # We don't start the thread, so we don't use UDP, but we fo test its logic
    # socket.sendto(f"hello {d}".encode(), ("127.0.0.1", 8125))

    receiver._process_data("traefik.service.requests.total count=32 ")
    receiver._process_data("traefik.service.connections.open value=4 ")
    receiver._process_data("traefik.service.request.duration p50=0.007,")

    data = collector.data
    assert len(data) == 3
    assert data[0] == ("system", {"count requests": 32})
    assert data[1] == ("system", {"num open-connections": 4})
    assert data[2] == ("system", {"num duration s": 0.007})


## Producer


def test_system_producer():
    class StubCollector:
        def __init__(self):
            self.data = []

        def put(self, category, **kwargs):
            self.data.append((category, kwargs))

    collector = StubCollector()
    producer = mypaas.stats.SystemStatsProducer(collector)

    # Run the producer for 1 second
    producer.start()
    time.sleep(1.2)
    producer._stop = True

    data = collector.data
    assert len(data) >= 1
    assert data[0][0] == "system"
    assert "num_cpu_perc" in data[0][1]
    assert 0 <= data[0][1]["num_cpu_perc"] <= 100


## Collector


def test_collector():
    clean_db()

    collector = StatsCollector(db_dir)
    assert collector.get_categories() == ()

    collector.put("bb", num_foo=3)
    collector.put("zz", num_foo=3)
    collector.put("aa", num_foo=3)
    collector.put("system", num_foo=3)

    # "system" comes first, then alphabetically
    assert collector.get_categories() == ("system", "aa", "bb", "zz")

    # Stop it
    for m in _monitor_instances:
        m.flush()
    del collector
    gc.collect()
    assert len(_monitor_instances) <= 1

    # The files are still there, and the collector picks them up
    collector = StatsCollector(db_dir)
    assert collector.get_categories() == ("system", "aa", "bb", "zz")


## Server


def test_server():
    clean_db()

    collector = StatsCollector(db_dir)
    collector.put("aaa", num_foo=3)
    collector.put("bbb", num_foo=3)

    main_handler = mypaas.stats.make_main_handler(collector)

    with asgineer.testutils.MockTestServer(main_handler) as server:

        # Root page
        r = server.request("GET", "/")
        assert r.status == 200
        assert r.body.startswith(b"<!DOCTYPE html>")
        assert b"aaa" in r.body
        assert b"bbb" in r.body
        assert b"ccc" not in r.body

        # Now add a measurement in a new category, and see that its in there
        collector.put("ccc", num_foo=3)
        r = server.request("GET", "/")
        assert b"aaa" in r.body
        assert b"bbb" in r.body
        assert b"ccc" in r.body

        # Empty stats redirects
        r = server.request("GET", "/stats")
        assert r.status == 302

        # Other stats get info
        r = server.request("GET", "/stats?categories=aa,bb")
        assert r.status == 200

        # Style sheet is separate
        r = server.request("GET", "/style.css")
        assert r.status == 200
        assert b"padding:" in r.body

        # Invalid
        assert server.request("PUT", "/").status == 405
        assert server.request("GET", "/no_valid_page").status == 404


##

# todo: revive this in another form?
# def test_speed():
#
#     clean_db()
#     m = SiteMonitor(filename)
#
#     t0 = time.perf_counter()
#     n = 10000
#     for i in range(n):
#         path = "".join(random.choice("abcdefg") for i in range(3))
#         status_code = random.choice([200, 200, 200, 304, 304, 404])
#         response_time = random.random()
#         headers = {
#             "x-real-ip": "127.0.0.1",
#             "user-agent": "Mozilla/5 Firefox" + path,
#             "accept-language": "nl",
#         }
#         with m:
#             m.put_request(path, headers, status_code, response_time)
#     t1 = time.perf_counter()
#     time_per_iter = (t1 - t0) / n
#     print(f"{time_per_iter*1000000:0.0f}us")
#     # assert time_per_iter < 0.0001  # Glitchy
#     assert time_per_iter < 0.001


if __name__ == "__main__":
    run_tests(globals())
