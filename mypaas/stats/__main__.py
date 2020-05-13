"""
Main script to run the stats server.
"""

import os

import asgineer

try:
    from stats import StatsCollector, UdpStatsReceiver
    from stats import stats_handler
except ImportError:
    from mypaas.stats import StatsCollector, UdpStatsReceiver
    from mypaas.stats import stats_handler


# Create a stats collector
db_dir = os.path.expanduser("~/_stats")
collector = StatsCollector(db_dir)

# Start a thread that receives stats via udp and puts it into the collector
udp_stats_receiver = UdpStatsReceiver(collector)
udp_stats_receiver.start()


@asgineer.to_asgi
async def main_handler(request):
    return await stats_handler(request, collector)


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
