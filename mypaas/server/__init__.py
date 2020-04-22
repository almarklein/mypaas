"""
This mypaas.server subpackage provides a CLI to run at the PaaS server
to manage it.

Dependencies: asgineer
"""

# flake8: noqa

from ._init import init, restart
from ._traefik import init_router, restart_router
from ._deploy import deploy, get_deploy_generator
from ._auth import get_public_key
from ._daemon import restart_daemon
from ._stats import restart_stats
from ._reboot import schedule_reboot
