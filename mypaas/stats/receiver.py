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
            category = "system"
            stats = self._process_data_traefik(text)
        elif text.startswith("{"):
            stats = json.loads(text)
            category = stats.pop("category", "other")
        else:
            category = "other"
            stats = self._process_data_statsd(text)

        self._collector.put(category, stats)

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
                        stats["requests|count"] = int(post.split(" ")[0])
                    except ValueError:  # pragma: no cover
                        pass
            elif line.startswith("traefik.service.connections.open"):
                _, sep, post = line.partition(" value=")
                if sep:
                    try:
                        stats["open connections|num"] = int(post.split(" ")[0])
                    except ValueError:  # pragma: no cover
                        pass
            elif line.startswith("traefik.service.request.duration"):
                _, sep, post = line.partition(" p50=")
                if sep:
                    try:
                        stats["duration|num|s"] = float(
                            post.split(" ")[0].split(",")[0]
                        )
                    except ValueError:  # pragma: no cover
                        pass
            else:
                pass  # drop it
        return stats

    def _process_data_statsd(self, text):
        """ Process statsd data.
        """
        stats = {}
        for line in text.splitlines():
            parts = line.split("|")
            if len(parts) >= 2:
                name_value, type, *_ = parts
                name, value = name_value.split(":")
                if type == "c":
                    stats[name + "|count"] = int(value)
                elif type == "m":  # meter
                    stats[name + "|count"] = int(value)
                elif type == "h":  # histogram
                    stats[name + "|num"] = float(value)
                elif type == "ms":
                    stats[name + "|num|s"] = float(value) / 1000
                elif type == "g":  # we map Gauge to a num
                    stats[name + "|num"] = float(value)
                elif type == "s":
                    stats[name + "|cat"] = value
        return stats
