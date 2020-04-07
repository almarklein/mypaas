"""
Main script to run the stats server.
"""

import os

import asgineer
from mypaas import StatsCollector, UdpStatsReceiver, SystemStatsProducer
from mypaas import make_main_handler


# Create a stats collector
db_dir = os.path.expanduser("~/_stats")
the_collector = StatsCollector(db_dir)

# Start a thread that will put system stats into the collector
system_stats_produder = SystemStatsProducer(the_collector)
system_stats_produder.start()

# Start a thread that receives stats via udp and puts it into the collector
udp_stats_receiver = UdpStatsReceiver(the_collector)
udp_stats_receiver.start()

# Create a server for the collector
main_handler = asgineer.to_asgi(make_main_handler(the_collector))


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80")
