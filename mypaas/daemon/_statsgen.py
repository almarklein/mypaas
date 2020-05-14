import json
import time
import socket
import logging
import threading

import psutil


logger = logging.getLogger("mypaas.daemon")

stats_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class SystemStatsProducer(threading.Thread):
    """ Thead that produces measurements on the system and mypaas services,
    and sends these stats to the mypaas stats server.
    Currently measuring CPU, RAM and disk.
    """

    def __init__(self):
        super().__init__()
        self.setDaemon(True)
        self._stop = False
        self._service_processes = {}
        self._create_times = {}

    def run(self):
        t = time.time()
        time1 = t + 1
        time10 = t + 3  # the first 10-tick comes sooner

        while not self._stop:
            time.sleep(0.05)
            t = time.time()

            if t > time1:
                time1 = t + 1
                try:
                    self._do_each_1_seconds()
                except Exception:  # pragma: no cover
                    pass

            if t > time10:
                time10 = t + 10
                try:
                    self._do_each_10_seconds()
                except Exception:  # pragma: no cover
                    pass

    def _send(self, stat):
        stats_socket.sendto(json.dumps(stat).encode(), ("localhost", 8125))

    def _do_each_1_seconds(self):
        self._measure_stats_of_system()
        self._measure_stats_of_services()

    def _do_each_10_seconds(self):
        self._measure_system_disk_usage()
        self._collect_services()
        self._detect_startups()

    def _measure_stats_of_system(self):
        try:
            stat = {
                "group": "system",
                "cpu|num|%": max(0.01, psutil.cpu_percent()),
                "mem|num|iB": psutil.virtual_memory().used,
            }
            self._send(stat)
        except Exception as err:  # pragma: no cover
            logger.error("Failed to send system measurements: " + str(err))

    def _measure_system_disk_usage(self):
        try:
            disk = psutil.disk_usage("/").used
            stat = {"group": "system", "disk|num|iB": disk}
            self._send(stat)
        except Exception as err:  # pragma: no cover
            logger.error("Failed to send system measurements: " + str(err))

    def _measure_stats_of_services(self):
        for container_name, p in self._service_processes.items():
            try:
                stat = {
                    "group": container_name,
                    "cpu|num|%": max(0.01, p.cpu_percent()),
                    "mem|num|iB": p.memory_info().rss,
                }
                self._send(stat)
            except Exception as err:  # pragma: no cover
                logger.error(
                    f"Failed to send {container_name} measurements: " + str(err)
                )

    def _detect_startups(self):
        for container_name, p in self._service_processes.items():
            # Get process creation time and our stored creation time
            try:
                create_time = p.create_time()
            except Exception:
                continue  # p.create_time may not be available on each OS
            ref_create_time = self._create_times.get(container_name, 0)
            # If it's different and uptime is less than a minute, assume its a startup
            # Note that we can get false positives if *this* process restarts within
            # a minute after another process does.
            if ref_create_time != create_time:
                self._create_times[container_name] = create_time
                uptime = time.time() - create_time
                if uptime < 60:
                    try:
                        stat = {
                            "group": container_name,
                            "startup|count": 1,
                        }
                        self._send(stat)
                    except Exception as err:  # pragma: no cover
                        logger.error(
                            f"Failed to send {container_name} startup: " + str(err)
                        )

    def _collect_services(self):
        try:
            processes = {}
            for p in psutil.process_iter():
                try:
                    container_name = p.environ().get("MYPAAS_CONTAINER", "")
                    if container_name:
                        processes[container_name] = p
                except Exception:  # pragma: no cover
                    pass
            self._service_processes = processes
        except Exception as err:  # pragma: no cover
            logger.error("Failed to collect service processes: " + str(err))
