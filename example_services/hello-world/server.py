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
    stat = {"category": os.getenv("MYPAAS_SERVICE_NAME", "")}
    stat["requests|count"] = 1
    stat["path|cat"] = f"{status_code} - {path}" if (status_code and path) else path
    if rtime is not None:
        stat["rtime|num|s"] = float(rtime)
    # For page views, anomimously register page view / visitors / country
    if is_page:
        stat["pageview"] = request.headers
    # Send over UDP
    # stats_socket.sendto(json.dumps(stat).encode(), ("stats", 8125))
    request.headers.setdefault("x-real-ip", "127.0.0.1")
    stats_socket.sendto(json.dumps(stat).encode(), ("localhost", 8125))


def send_pageview_stat(request, status_code, rtime):

    #
    # # Additional data for a page-view
    # stat["views|count"] = 1
    # referer = headers.get("referer", "")
    # if referer:
    #     referer = referer.split("://")[-1].split("/")[0].split(":")[0]
    #     stat["referer|cat"] = referer
    # # Additional data to derive per-user info (browser, language, more)
    # ip = headers.get("x-forwarded-for", "") or headers.get("x-real-ip", "")
    # ip = ip or request.scope["client"][0]
    # ua = headers.get("user-agent", "")
    # if ip and ua:
    #     stat["userdata"] = {
    #         "ip": ip,
    #         "user-agent": ua,
    #         "accept-language": headers.get("accept-language", ""),
    #     }
    stats_socket.sendto(json.dumps(stat).encode(), ("stats", 8125))


@asgineer.to_asgi
async def main_handler(request):

    d = datetime.datetime.now()
    p = request.path

    send_stat(request, 200)
    return 200, {}, f"Hello world! Server time: {d}, path: {p}"


if __name__ == "__main__":
    os.environ.setdefault("MYPAAS_SERVICE_NAME", "hello-world")
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:81", log_level="warning")
