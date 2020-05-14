import os
import time
import random
import sqlite3
import tempfile
import threading
from contextlib import closing

from pytest import raises

from testutils import run_tests
from mypaas.stats._itemdb import ItemDB


def get_fresh_filename():
    filename = os.path.join(tempfile.gettempdir(), "test.db")
    if os.path.isfile(filename):
        os.remove(filename)
    return filename


def test_init_read():

    # Empty database, zero tables

    db = ItemDB(":memory:")

    assert db.get_table_info() == []  # no tables

    with raises(KeyError):
        db.select("foo", "key is NULL")
    with raises(KeyError):
        db.select_all("foo")
    with raises(KeyError):
        db.count_all("foo")

    # Two tables

    db = ItemDB(":memory:").ensure("foo", "key").ensure("bar")

    assert "[]" not in repr(db)
    assert db.get_table_info()[0][0] == "bar"
    assert db.get_table_info()[1][0] == "foo"
    assert db.count_all("foo") == 0
    assert db.count_all("bar") == 0


def test_table_fails():

    db = ItemDB(":memory:")
    for name in [(), 4, b"", [], {}]:
        with raises(TypeError):  # not a str
            db.ensure(name)

    db = ItemDB(":memory:")
    for name in ["foo bar", "foo-bar", "33", "foo!", "!foo"]:
        with raises(ValueError):  # not an identifier
            db.ensure(name)


def test_index_fails():

    # Invalid index/table names - not str
    db = ItemDB(":memory:")
    for name in [(), 4, b"", [], {}]:
        with raises(TypeError):
            db.ensure("items", name)

    # Invalid index/table names - not an identifier
    db = ItemDB(":memory:")
    for name in ["foo bar", "foo-bar", "33", "foo!"]:
        with raises(ValueError):
            db.ensure("items", name)

    # Reserved
    for name in ["!_ob", "_ob"]:
        with raises(IndexError):
            db.ensure("items", name)

    # Cannot add a unique key

    filename = get_fresh_filename()
    db = ItemDB(filename).ensure("foo", "meh")
    with closing(db):

        assert "foo" in [x[0] for x in db.get_table_info()]

        with raises(IndexError):
            db = ItemDB(filename).ensure("foo", "!key")

    # Cannot use a normal key as a unique key

    filename = get_fresh_filename()
    db = ItemDB(filename).ensure("foo", "key")
    with closing(db):

        assert "foo" in [x[0] for x in db.get_table_info()]

        with raises(IndexError):
            db = ItemDB(filename).ensure("foo", "!key")

    # Cannot use a unique key as a normal key

    filename = get_fresh_filename()
    db = ItemDB(filename).ensure("foo", "!key")
    with closing(db):

        assert "foo" in [x[0] for x in db.get_table_info()]

        with raises(IndexError):
            db = ItemDB(filename).ensure("foo", "key")


def test_init_write():
    db = ItemDB(":memory:").ensure("items", "!id", "mt")

    with raises(IOError):  # Put needs to be used under a context
        db.put("items", dict(id=1, mt=100))

    with raises(KeyError):  # Invalid table
        with db:
            db.put("foo", dict(id=1, mt=100))

    with raises(TypeError):  # Note a dict
        with db:
            db.put("items", "not a dict")

    with raises(IndexError):  # id is required but missing
        with db:
            db.put("items", dict(mt=100))

    with raises(IOError):  # Cant enter twice
        with db:
            with db:
                pass

    with db:
        db.put("items", dict(id=1, mt=100))
        db.put("items", dict(id=2, mt=100, value=42))
        db.put("items", dict(id=3, value=42))

    assert len(db.select_all("items")) == 3
    assert db.count_all("items") == 3
    assert len(db.get_table_info()) == 1

    assert len(db.select("items", "mt == 100")) == 2
    assert len(db.select("items", "mt is NULL")) == 1
    assert db.count("items", "mt == 100") == 2
    assert db.count("items", "mt is NULL") == 1
    with raises(IndexError):  # No index for value
        db.select("items", "value == 42")
    with raises(IndexError):  # No index for value
        db.count("items", "value == 42")
    with raises(sqlite3.OperationalError):  # Malformed SQL
        db.select("items", "id >>> 42")
    with raises(sqlite3.OperationalError):  # Malformed SQL
        db.count("items", "id >>> 42")


def test_multiple_unique_keys():

    db = ItemDB(":memory:").ensure("items", "!id1", "!id2")

    with db:
        db.put_one("items", id1=1, id2=1, value=1)
        db.put_one("items", id1=1, id2=2, value=2)
        db.put_one("items", id1=2, id2=2, value=3)
        db.put_one("items", id1=2, id2=1, value=4)

    assert db.count_all("items") == 1
    assert db.select_one("items", "id1 == 1") is None
    assert db.select_one("items", "id1 == 2")["value"] == 4


def test_missing_values1():

    filename = get_fresh_filename()

    db = ItemDB(filename).ensure("items", "!id", "mt")

    # Keys that are not listed are NOT ignored
    with db:
        db.put("items", dict(id=1, mt=100))
        db.put("items", dict(id=2, mt=100, value=6))
    #
    assert db.select_all("items") == [dict(id=1, mt=100), dict(id=2, mt=100, value=6)]
    with raises(IndexError):  # No index for value
        db.select("items", "value == 6")

    # When a column is added it gets NULL values in the db, and items stay as they are
    db = ItemDB(filename).ensure("items", "!id", "mt", "value")
    with db:
        db.put("items", dict(id=3, mt=100, value=41))
    #
    db = ItemDB(filename).ensure("items", "!id", "mt", "value")
    assert db.select_all("items") == [
        dict(id=1, mt=100),
        dict(id=2, mt=100, value=6),
        dict(id=3, mt=100, value=41),
    ]

    assert len(db.select("items", "value == 6")) == 1
    assert len(db.select("items", "value > 0")) == 2
    assert len(db.select("items", "value is NULL")) == 1

    # When we don't specify a column, it still gets a value (not NULL)

    db = ItemDB(filename).ensure("items", "!id")
    with db:
        db.put("items", dict(id=5, mt=100, value=999))
    assert len(db.select("items", "value == 999")) == 1


def test_missing_values2():

    filename = get_fresh_filename()

    db = ItemDB(filename)
    db.ensure("items", "!id", "mt")

    # Keys that are not listed are NOT ignored
    with db:
        db.put("items", dict(id=1, mt=100))
        db.put("items", dict(id=2, mt=100, value=6))
    #
    assert db.select_all("items") == [dict(id=1, mt=100), dict(id=2, mt=100, value=6)]
    with raises(IndexError):  # No index for value
        db.select("items", "value == 6")

    # When a column is added it gets NULL values in the db, and items stay as they are
    db.ensure("items", "value")
    with db:
        db.put("items", dict(id=3, mt=100, value=41))
    #
    assert db.select_all("items") == [
        dict(id=1, mt=100),
        dict(id=2, mt=100, value=6),
        dict(id=3, mt=100, value=41),
    ]

    assert len(db.select("items", "value == 6")) == 1
    assert len(db.select("items", "value > 0")) == 2
    assert len(db.select("items", "value is NULL")) == 1

    # When we don't specify a column, it still gets a value (not NULL)
    db = ItemDB(filename)
    with db:
        db.put("items", dict(id=5, mt=100, value=999))
    assert len(db.select("items", "value == 999")) == 1


def test_usage_items():

    db = ItemDB(":memory:").ensure("items", "!id", "mt", "value")

    # Need id
    with raises(IndexError):
        with db:
            db.put("items", dict(mt=100, value=1))

    # Add three items
    with db:
        db.put("items", dict(id=1, mt=100, value=1))
        db.put("items", dict(id=2, mt=100, value=1))
        db.put("items", dict(id=3, mt=100, value=1))

    assert len(db.select_all("items")) == 3
    assert len(db.select("items", "value == 1")) == 3
    assert len(db.select("items", "value == 2")) == 0

    # Update them, one using an older mt
    for item in [
        dict(id=1, mt=99, value=2),  # wont override
        dict(id=2, mt=100, value=2),  # will override - mt's are equal
        dict(id=3, mt=101, value=2),  # will override
        dict(id=4, mt=101, value=2),  # new
    ]:
        with db:
            cur = db.select("items", "id == ?", item["id"])
            if not cur or cur[0]["mt"] <= item["mt"]:
                db.put("items", item)

    assert len(db.select_all("items")) == 4
    assert len(db.select("items", "value == 1")) == 1
    assert len(db.select("items", "value == 2")) == 3

    x = db.select_one("items", "id == ?", 3)
    assert x["mt"] == 101

    db = ItemDB(":memory:").ensure("items", "!id", "mt", "value")
    x = db.select_one("items", "id == ?", 3)
    assert x is None


def test_usage_settings():

    db = ItemDB(":memory:").ensure("settings", "!id", "mt", "value")

    # Need id
    with raises(IndexError):
        with db:
            db.put("settings", dict(value="old", mt=100))

    # Add three items
    with db:
        db.put("settings", dict(id="foo", value="old", mt=100))
        db.put("settings", dict(id="bar", value="old", mt=100))
        db.put("settings", dict(id="egg", value="old", mt=100))

    assert len(db.select_all("settings")) == 3
    assert len(db.select("settings", "mt > 100")) == 0
    assert len(db.select("settings", "value == 'updated'")) == 0

    # Update them, one using an older
    for item in [
        dict(id="foo", value="updated", mt=99),
        dict(id="bar", value="updated", mt=100),  # also updates
        dict(id="egg", value="updated", mt=101),
        dict(id="spam", value="updated", mt=101),  # new
    ]:
        with db:
            cur = db.select("settings", "id == ?", item["id"])
            if not cur or cur[0]["mt"] <= item["mt"]:
                db.put("settings", item)

    assert len(db.select_all("settings")) == 4
    assert len(db.select("settings", "mt > 100")) == 2
    assert len(db.select("settings", "value == 'updated'")) == 3
    assert db.select_one("settings", "id=='egg'")["value"] == "updated"


def test_multiple_items():

    filename = get_fresh_filename()

    db = ItemDB(filename)
    db.ensure("items", "!id")

    assert len(db.select_all("items")) == 0

    # Adding multiple
    with db:
        db.put("items", dict(id=1, mt=100), dict(id=2, mt=100))

    assert len(db.select_all("items")) == 2

    # Separate additions, one gets added
    # These few tests here are a remnant of when itemdb was different, but lets
    # not throw away precious testing code ...
    with db:
        db.put("items", dict(id=3, mt=100))
    with raises(RuntimeError):
        with db:
            raise RuntimeError()

    assert set(x["id"] for x in db.select_all("items")) == {1, 2, 3}

    # Combined addition, none gets added
    with raises(RuntimeError):
        with db:
            db.put("items", dict(id=4, mt=100), dict(id=5))
            raise RuntimeError()

    assert set(x["id"] for x in db.select_all("items")) == {1, 2, 3}

    # Combined addition, none gets changed
    with raises(RuntimeError):
        with db:
            db.put("items", dict(id=3, mt=102), dict(id=5))
            raise RuntimeError()

    assert set(x["id"] for x in db.select_all("items")) == {1, 2, 3}
    x = db.select_all("items")[-1]
    assert x["id"] == 3 and x["mt"] == 100

    # Upgrades work too
    db = ItemDB(filename)

    with db:
        db.put(
            "items",
            dict(id=1, mt=102),
            dict(id=1, mt=102),
            dict(id=2, mt=102),
            dict(id=3, mt=102),
            dict(id=4, mt=102),
        )
    assert set(x["id"] for x in db.select_all("items")) == {1, 2, 3, 4}
    for x in db.select_all("items"):
        x["mt"] == 102

    # Lets take it further
    with db:
        db.put("items", *(dict(id=i, mt=104) for i in range(99)))
    assert len(db.select_all("items")) == 99


def test_transactions1():

    filename = get_fresh_filename()

    db = ItemDB(filename)
    db.ensure("items", "!id", "mt")

    # Add items the easy way
    with db:
        db.put_one("items", id=1, mt=100)
        db.put_one("items", id=2, mt=100)
    assert db.count_all("items") == 2

    # Add more items and raise after
    with raises(RuntimeError):
        with db:
            db.put_one("items", id=3, mt=100)
            db.put_one("items", id=4, mt=100)
        raise RuntimeError("Transaction has been comitted")
    assert db.count_all("items") == 4

    # Again, but now raise within transaction
    with raises(RuntimeError):
        with db:
            db.put_one("items", id=5, mt=100)
            db.put_one("items", id=6, mt=100)
            raise RuntimeError("Abort transaction!")
    assert db.count_all("items") == 4


def test_transactions2():

    filename = get_fresh_filename()
    with ItemDB(filename).ensure("items", "!id") as db:
        db.put_one("items", id=3, value=10)

    # run transactions in threads while reading from other threads
    def run_slow_transaction1():
        db = ItemDB(filename)
        with db:
            db.put_one("items", id=3, value=20)
            time.sleep(1.0)

    def run_fast_transaction2():
        db = ItemDB(filename)
        time.sleep(0.1)  # make sure that we're the waiting thread
        with db:
            db.put_one("items", id=3, value=30)
            time.sleep(0.2)

    def run_read():
        db = ItemDB(filename)
        for i in range(30):
            time.sleep(0.05)
            item = db.select_one("items", "id == 3")
            read.append(item["value"])

    read = []
    threads = [
        threading.Thread(target=run_slow_transaction1),
        threading.Thread(target=run_fast_transaction2),
        threading.Thread(target=run_read),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(read) == 30
    assert 15 <= read.count(10) <= 22
    assert 2 <= read.count(20) <= 6
    assert read.count(30) >= 5


def test_transactions3():
    # Test that a transaction really blocks

    filename = get_fresh_filename()

    def run_slow_transaction():
        db = ItemDB(filename)
        with db:
            time.sleep(0.2)

    threads = [threading.Thread(target=run_slow_transaction) for i in range(3)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    etime = time.perf_counter() - t0

    print(etime)
    assert etime > 0.6


def test_database_race_conditions():

    # This actually tests that a specific update scheme works with the
    # itemdb. It should. In a previous version, itemdb was specifically
    # designed for this syncing task. Now it's more general, but this
    # is still a good use-case.

    n_threads = 25
    n_writes = 25
    tracking = {}
    for i in range(1, 11):
        tracking[i] = []

    # Create db and ensure it has tables
    filename = get_fresh_filename()
    ItemDB(filename).ensure("items", "!id")

    def push_a_bunch():
        for i in range(n_writes):
            id = random.randint(1, 10)
            mt = random.randint(1000, 2000)
            tracking[id].append(mt)
            with ItemDB(filename) as db:
                x = db.select_one("items", "id == ?", id)
                if not x or x["mt"] <= mt:
                    db.put_one("items", id=id, mt=mt)

    # Prepare, start, and join threads
    t0 = time.perf_counter()
    threads = [threading.Thread(target=push_a_bunch) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t1 = time.perf_counter()

    # Evaluate the result
    items = ItemDB(filename).select_all("items")
    print(
        f"{t1 - t0:0.2f} s for {n_threads * n_writes} writes saving {len(items)} items"
    )
    assert len(items) == 10  # that's the number of id's
    #
    for item in items:
        id = item["id"]
        assert item["mt"] == max(tracking[id])

    return items


def test_threaded_access():
    """ This was an attempt to reproduce an error that turned out to be related
    to the discrepancy between os.path.getmtime and server_time. This test helped
    establish that it was not in itemdb.
    """
    filename = get_fresh_filename()

    xx = []

    def write_something():
        db = ItemDB(filename).ensure("settings", "!id")
        with db:
            db.put("settings", dict(id="server_reset", value="42", mt=42))
        db.close()
        return "wrote something"

    def read_something():
        db = ItemDB(filename).ensure("settings", "!id")
        xx.extend(db.select_all("settings"))
        return "read something"

    t = threading.Thread(target=write_something)
    t.start()
    t.join()
    t = threading.Thread(target=read_something)
    t.start()
    t.join()

    assert len(xx) == 1


if __name__ == "__main__":
    run_tests(globals())
