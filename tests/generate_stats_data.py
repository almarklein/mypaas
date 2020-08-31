"""
Generate some stats data so that if we run mypaas.stats locally,
we have some data to look at, even if it's fake :)
"""

import os
import time
import random
import datetime

from mypaas.stats import Monitor


def generate_test_data(filename, ndays=10):
    """Generate test data to test the get_data() and website."""
    utc = datetime.timezone.utc
    today = time.gmtime()  # UTC
    today = datetime.datetime(today.tm_year, today.tm_mon, today.tm_mday, tzinfo=utc)
    first_day = today - datetime.timedelta(days=ndays)
    one_day = datetime.timedelta(days=1)

    step = 600  # default 10 min

    # Refuse if log db exists
    if os.path.isfile(filename):
        os.remove(filename)

    monitor = Monitor(filename, step=step)

    visitor_ids = set(range(random.randint(10000, 80000)))

    # Produce data
    day = first_day
    monitor._monthly_ids = {}
    while day < today:
        day += one_day
        print("Generating for", day)
        monitor._daily_ids = {}
        for b in range(int(86400 / step)):
            with monitor:
                # Generate some request data
                for i in range(random.randint(1000, 2000)):
                    monitor.put("requests|count", 1)
                for i in range(random.randint(300, 1200)):
                    monitor.put("views|count", 1)
                for i in random.sample(visitor_ids, random.randint(10, 80)):
                    monitor.put("visits|dcount", i)
                    monitor.put("visits|mcount", i)
                # Generate some random OS and status data
                for i in range(random.randint(5, 30)):
                    osname = random.choice(["Windows", "Windows", "Linux", "OS X"])
                    browsername = random.choice(
                        ["FF", "FF", "Chrome", "Edge", "Safari"]
                    )
                    monitor.put("browser|cat", browsername + " - " + osname)
                # Generate some cpu and mem data
                for i in range(random.randint(5, 30)):
                    monitor.put("cpu|num|perc", random.randint(10, 70))
                for i in range(random.randint(5, 30)):
                    monitor.put("mem|num|iB", random.randint(2 * 2 ** 30, 8 * 2 ** 30))
            # Write!
            aggr = monitor._next_aggr()
            t = int(day.timestamp() + b * step)
            key = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))
            aggr["time_key"] = key
            aggr["time_start"] = t
            aggr["time_stop"] = t + step
            monitor._write_aggr(aggr)


if __name__ == "__main__":
    generate_test_data(os.path.expanduser("~/_stats/exampledata.db"))
