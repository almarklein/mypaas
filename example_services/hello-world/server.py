import os
import time
import json
import socket
import datetime

import asyncpg
import asgineer


stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_stats(request, status_code=None, rtime=None, is_page=None):
    """Send request stats over UPD to a stats server."""
    p = request.path
    stats = {"group": os.getenv("MYPAAS_SERVICE", "")}
    stats["requests|count"] = 1
    stats["path|cat"] = f"{status_code} - {p}" if (status_code and p) else p
    if rtime is not None:
        stats["rtime|num|s"] = float(rtime)
    if is_page:  # anomimously register page view, visitors, language, and more
        stats["pageview"] = request.headers
    stats_socket.sendto(json.dumps(stats).encode(), ("stats", 8125))


@asgineer.to_asgi
async def main_handler(request):
    if request.path.startswith("/postgres"):
        return await postgres_example_handler(request)
    else:
        return await default_handler(request)


async def default_handler(request):
    p = request.path
    is_page = "." not in p or p.endswith(".html")
    send_stats(request, 200, is_page=is_page)
    container = os.getenv("MYPAAS_CONTAINER", "")
    d = datetime.datetime.now()
    return 200, {}, f"Hello world! Server time: {d}, path: {p}, container: {container}"


async def postgres_example_handler(request):
    conn = await asyncpg.connect(
        user="postgres", password="1234", database="postgres", host="postgres"
    )

    # Add entry in table. Create table if needed
    try:
        await conn.fetch("""INSERT INTO visitors(timestamp) VALUES($1)""", time.time())
    except asyncpg.UndefinedTableError:
        await conn.fetch(
            """CREATE TABLE visitors(
            timestamp INT NOT NULL
            );"""
        )

    # Get how many visits we've had (number of rows in the table)
    values = await conn.fetch("""SELECT COUNT(*) FROM visitors""")
    nvisits = values[0]["count"]
    await conn.close()

    # Return response
    return 200, {}, f"We've had {nvisits} visits"


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
