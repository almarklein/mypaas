"""
The mypaas.daemon subpackage is started as a systemctl service, and
provides an API to push deploys and poll the PaaS status.

Dependencies: asgineer, psutil
"""

# flake8: noqa

from ._api import main_handler
from ._statsgen import SystemStatsProducer
