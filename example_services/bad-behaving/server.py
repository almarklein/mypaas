import os
import json
import time
import socket


startup_stats = {"group": os.getenv("MYPAAS_CONTAINER", ""), "startup|count": 1}
stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stats_socket.sendto(json.dumps(startup_stats).encode(), ("stats", 8125))


if __name__ == "__main__":

    chunks = []
    while True:
        etime = time.time() + 1
        while time.time() < etime:
            pass
        chunks.append("x" * 2 ** 20)
