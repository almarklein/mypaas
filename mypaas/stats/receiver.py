import json
import socket
import hashlib
import threading

from fastuaparser import parse_ua

from .monitor import logger


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
                self.process_data(data.decode(errors="ignore"))
            except Exception:
                pass

    def process_data(self, text):
        """ Parse incoming data and put it into the collector.
        """
        if text.startswith("traefik"):
            group = "traefik"
            stats = self._process_data_traefik(text)
        elif text.startswith("pageview:"):
            stats = self._process_data_pageview(text)
        elif text.startswith("{"):
            stats = json.loads(text)
            group = stats.pop("group", "") or "other"
            pageview = stats.pop("pageview", None)
            if pageview:
                self._process_pageview(group, pageview)
        else:
            group = "other"
            stats = self._process_data_statsd(text)

        self._collector.put(group, stats)

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

    def _process_pageview(self, group, headers):
        stats = {}
        try:
            stats["views|count"] = 1
            # Process referer
            referer = headers.get("referer", "")
            if referer:
                referer = referer.split("://")[-1].split("/")[0].split(":")[0]
                stats["referer|cat"] = referer
            # Use IP and user-agent to identify a user, anomimously
            # NOTE: this assumes there is a reverse proxy in front
            ip = headers.get("x-forwarded-for", "") or headers.get("x-real-ip", "")
            ua = headers.get("user-agent", "")
            lang = headers.get("accept-language", "")
            if ip and ua:
                # Get unique user string and turn it into a unique int
                client_id = ip + ua
                client_id = hashlib.md5(client_id.encode())
                client_id = abs(
                    int(client_id.hexdigest()[:14], 16)
                )  # 7 bytes fits in int64
                # Register daily visit of this user, and if its a new user, submit more
                new_user = self._collector.put_one(group, "visits|dcount", client_id)
                if new_user:
                    stats["visits|mcount"] = client_id
                    stats["client|cat"] = parse_ua(ua)  # OS and browser
                    if lang:
                        lang = lang.split(";")[0].split(",")[0].strip().lower()
                        stats["language|cat"] = lang.replace("-", " - ")
                    # todo: get country from ip
            self._collector.put(group, stats)
        except Exception as err:
            logger.error("Error processing pageview: " + str(err))

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
