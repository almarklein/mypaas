import os
import json
import socket
import datetime

import asgineer


stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_stat(request, status_code=None, rtime=None, is_page=None):
    path = request.path
    if is_page is None:
        is_page = path and ("." not in path or path.endswith(".html"))
    # Build request stat
    stat = {"group": os.getenv("MYPAAS_SERVICE_NAME", "")}
    stat["requests|count"] = 1
    stat["path|cat"] = f"{status_code} - {path}" if (status_code and path) else path
    if rtime is not None:
        stat["rtime|num|s"] = float(rtime)
    # For page views, anomimously register page view / visitors / country
    if is_page:
        stat["pageview"] = request.headers
    # Send over UDP
    stats_socket.sendto(json.dumps(stat).encode(), ("stats", 8125))


@asgineer.to_asgi
async def main_handler(request):

    d = datetime.datetime.now()
    p = request.path

    send_stat(request, 200)
    return 200, {}, f"Hello world! Server time: {d}, path: {p}"


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
