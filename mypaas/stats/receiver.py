import json
import socket
import threading


class UdpStatsReceiver(threading.Thread):
    """ Thread that receives stats from UDP, send by other processes.
    Accepts (most of) statsd format, and a wee bit influxDB because that's
    what Traefik sends us.

    Processes the data and puts it into the collector.
    """

    def __init__(self, collector, port=8125):
        super().__init__()
        self._collector = collector
        self._port = port
        self.setDaemon(True)  # don't let this thread prevent shutdown
        self._stop = False

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", self._port))

        while not self._stop:
            data, addr = s.recvfrom(4096)
            try:
                self._process_data(data.decode(errors="ignore"))
            except Exception:
                pass

    def _process_data(self, text):
        """ Parse incoming data and put it into the collector.
        """
        if text.startswith("traefik"):
            category, stats = self._process_data_traefik(text)
        else:
            stats = json.loads(text)
            category = stats.pop("category", "other")

        self._collector.put(category, **stats)

    def _process_data_traefik(self, text):
        """ Parsers a tiny and Traefik-specific set of influxDB.
        """
        stats = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("traefik.service.requests.total"):
                _, sep, post = line.partition(" count=")
                if sep:
                    try:
                        stats["count requests"] = int(post.split(" ")[0])
                    except ValueError:  # pragma: no cover
                        pass
            elif line.startswith("traefik.service.connections.open"):
                _, sep, post = line.partition(" value=")
                if sep:
                    try:
                        stats["num open-connections"] = int(post.split(" ")[0])
                    except ValueError:  # pragma: no cover
                        pass
            elif line.startswith("traefik.service.request.duration"):
                _, sep, post = line.partition(" p50=")
                if sep:
                    try:
                        stats["num duration s"] = float(
                            post.split(" ")[0].split(",")[0]
                        )
                    except ValueError:  # pragma: no cover
                        pass
            else:
                pass  # drop it
        return "system", stats
