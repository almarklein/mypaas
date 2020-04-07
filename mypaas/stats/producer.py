import time
import logging
import threading

import psutil


logger = logging.getLogger("mypaas_stats")


class SystemStatsProducer(threading.Thread):
    """ Thead that produces system measurements and puts it into the collector.
    Currently measuring CPU, RAM and ssd.
    """

    def __init__(self, collector):
        super().__init__()
        self._collector = collector
        self.setDaemon(True)
        self._stop = False

    def run(self):
        t = time.time()
        time1 = t + 1
        time10 = t + 10

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

    def _do_each_1_seconds(self):
        try:
            # Measure for system (host system when using Docker)
            syscpu = psutil.cpu_percent()  # avg since last call, over all cpus
            sysmem = psutil.virtual_memory().used
            # Put in store
            items = {"sys cpu|num|%": max(syscpu, 0.01), "sys mem|num|iB": sysmem}
            self._collector.put("system", items)
        except Exception as err:  # pragma: no cover
            logger.error("Failed to put system measurements: " + str(err))

    def _do_each_10_seconds(self):
        try:
            # Measure for system (host system when using Docker)
            disk = psutil.disk_usage("/").used
            self._collector.put("system", {"sys disk|num|iB": disk})
        except Exception as err:  # pragma: no cover
            logger.error("Failed to put system measurements: " + str(err))
