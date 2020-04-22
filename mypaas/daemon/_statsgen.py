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
        for service_name, p in self._service_processes.items():
            try:
                stat = {
                    "group": service_name,
                    "cpu|num|%": max(0.01, p.cpu_percent()),
                    "mem|num|iB": p.memory_info().rss,
                }
                self._send(stat)
            except Exception as err:  # pragma: no cover
                logger.error(f"Failed to send {service_name} measurements: " + str(err))

    def _collect_services(self):
        try:
            processes = {}
            for p in psutil.process_iter():
                try:
                    service_name = p.environ().get("MYPAAS_SERVICE_NAME", "")
                    if service_name:
                        processes[service_name] = p
                except Exception:  # pragma: no cover
                    pass
            self._service_processes = processes
        except Exception as err:  # pragma: no cover
            logger.error("Failed to collect service processes: " + str(err))
