"""
The mypaas.stats subpackage represents a service to collect and view
all sorts of stats of your PaaS. All services can push measurements
over UDP.

Dependencies: fastuaparser, asgineer, pscript,
"""

# flake8: noqa
from .monitor import Monitor
from .collector import StatsCollector
from .receiver import UdpStatsReceiver
from .server import stats_handler
