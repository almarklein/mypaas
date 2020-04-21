import os
import json
import socket
import datetime

import asgineer


stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_stats(request, status_code=None, rtime=None, is_page=None):
    """ Send request stats over UPD to a stats server. """
    p = request.path
    stats = {"group": os.getenv("MYPAAS_SERVICE_NAME", "")}
    stats["requests|count"] = 1
    stats["path|cat"] = f"{status_code} - {p}" if (status_code and p) else p
    if rtime is not None:
        stats["rtime|num|s"] = float(rtime)
    if is_page:  # anomimously register page view, visitors, language, and more
        stats["pageview"] = request.headers
    stats_socket.sendto(json.dumps(stats).encode(), ("stats", 8125))


@asgineer.to_asgi
async def main_handler(request):

    d = datetime.datetime.now()
    p = request.path

    is_page = "." not in p or p.endswith(".html")
    send_stats(request, 200, is_page=is_page)
    return 200, {}, f"Hello world! Server time: {d}, path: {p}"


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
