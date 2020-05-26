"""
Run this from your workstation, or anywhere, to connect to your server and stress it!
"""

import time
import random
import threading

import requests

names = [f"foo{i}" for i in range(1000)]


##

# Run this once to create a bunch of databases at the server
if True:
    for name in names:
        print(name)
        items = [dict(key=str(i), value=random.random()) for i in range(10000)]
        r = requests.put(
            f"https://mypaas2.canpute.com/dbtest/sqlite/{name}", json={"items": items}
        )
        assert r.status_code == 200

##


N = 99
nthreads = 20

counters = [0 for i in range(nthreads)]
statuses = [0 for i in range(nthreads)]


def print_status(clear=True):
    text = " ".join([f"{x:02d}" for x in counters])
    if clear:
        text = "\b" * len(text) + text
    print(text, end="")


def make_query_some(thread_index):
    def query_some():
        try:
            for i in range(N):
                user = names[random.randint(0, len(names) - 1)]
                r = requests.get("https://mypaas2.canpute.com/dbtest/sqlite/" + user)
                assert r.status_code == 200
                counters[thread_index] += 1
        finally:
            statuses[thread_index] = 1

    return query_some


threads = [threading.Thread(target=make_query_some(i)) for i in range(nthreads)]

t0 = time.perf_counter()

for t in threads:
    t.start()

print_status(False)
while not all(statuses):
    time.sleep(0.2)
    print_status()
print()

t1 = time.perf_counter()
print((N * nthreads) / (t1 - t0), "RPS")
