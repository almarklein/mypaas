import os
import sys
import time
import random
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

import asgineer
import mypaas.stats as stats


filename = os.path.expanduser("~/stats_example.db")


def generate_test_data(filename, ndays=10):
    """ Generate test data to test the get_data() and website.
    """
    utc = datetime.timezone.utc
    today = time.gmtime()  # UTC
    today = datetime.datetime(today.tm_year, today.tm_mon, today.tm_mday, tzinfo=utc)
    first_day = today - datetime.timedelta(days=ndays)
    one_day = datetime.timedelta(days=1)

    step = 600  # default 10 min

    # Refuse if log db exists
    if os.path.isfile(filename):
        raise RuntimeError(
            f"generate_test_data() wont do unless there is no db ({filename})."
        )

    monitor = stats.Monitor(filename, step=step)

    # Produce data
    day = first_day
    while day < today:
        day += one_day
        print("Generating for", day)
        for b in range(int(86400 / step)):
            with monitor:
                # Generate some request data
                for i in range(random.randint(1000, 2000)):
                    monitor.put("count_requests", 1)
                for i in range(random.randint(300, 1200)):
                    monitor.put("count_views", 1)
                for i in range(random.randint(100, 800)):
                    monitor.put("dcount_visits", i)
                # Generate some random OS and status data
                for i in range(random.randint(5, 30)):
                    osname = random.choice(["Windows", "Windows", "Linux", "OS X"])
                    browsername = random.choice(
                        ["FF", "FF", "Chrome", "Edge", "Safari"]
                    )
                    monitor.put("cat_browser", browsername + " - " + osname)
                # Generate some cpu and mem data
                for i in range(random.randint(5, 30)):
                    monitor.put("num_cpu_perc", random.randint(10, 70))
                for i in range(random.randint(5, 30)):
                    monitor.put("num_mem_iB", random.randint(2 * 2 ** 30, 8 * 2 ** 30))
            # Write!
            monitor._daily_ids = {}
            aggr = monitor._next_aggr()
            t = int(day.timestamp() + b * step)
            key = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))
            aggr["time_key"] = key
            aggr["time_start"] = t
            aggr["time_stop"] = t + step
            monitor._write_aggr(aggr)


@asgineer.to_asgi
async def handler(request):
    ndays = request.querydict.get("ndays", "")
    daysago = request.querydict.get("daysago", "")
    return stats.get_webpage(ndays, daysago, [filename])


def main():

    # Generate data?
    # if not os.path.isfile(filename):
    #     generate_test_data(filename, 10)

    # Create aggregators
    # monitor1 = stats.Monitor(filename)  # noqa
    # pmonito2 = stats.ProcessMonitor(filename)  # noqa

    # Serve
    asgineer.run(stats.main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")


if __name__ == "__main__":
    main()
