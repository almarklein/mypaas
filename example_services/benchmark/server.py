import os
import json
import time
import socket
import asyncio

import itemdb
import asgineer


stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_stats(rtime):
    """Send request stats over UPD to a stats server."""
    stats = {"group": os.getenv("MYPAAS_SERVICE", "")}
    stats["requests|count"] = 1
    stats["rtime|num|s"] = float(rtime)
    try:
        stats_socket.sendto(json.dumps(stats).encode(), ("stats", 8125))
    except Exception:
        pass


@asgineer.to_asgi
async def main_handler(request):
    t0 = time.perf_counter()

    if request.path.startswith("/benchmark/noop"):
        response = 200, {}, b""
    elif request.path.startswith("/benchmark/sleep"):
        await asyncio.sleep(1)
        response = 200, {}, b""
    elif request.path.startswith("/benchmark/sqlite/"):
        response = await api_handler(request)
    else:
        return 404, {}, f"not {request.path}"

    t1 = time.perf_counter()
    send_stats(t1 - t0)

    return response


async def api_handler(request):

    user = request.path.split("/")[-1]
    filename = os.path.join("/root/_benchmark/" + user)
    db = itemdb.ItemDB(filename)
    db.ensure_table("items", "!key", "value")

    if request.method == "GET":
        items = db.select("items", "value < 0.1")
        return 200, {}, {"items": items}
    elif request.method == "PUT":
        ob = await request.get_json(1 * 2 ** 20)
        items = ob["items"]
        with db:
            db.put("items", *items)
        return 200, {}, b""


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
