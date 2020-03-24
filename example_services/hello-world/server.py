import socket
import datetime

import asgineer


stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


@asgineer.to_asgi
async def main_handler(request):

    d = datetime.datetime.now()
    p = request.path

    stats_socket.sendto(f"hello {d}".encode(), ("stats", 8125))
    return 200, {}, f"Hello world! Server time: {d}, path: {p}"


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
