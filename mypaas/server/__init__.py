"""
This mypaas.server subpackage provides a CLI to run at the PAAS server
to manage it.
"""

# flake8: noqa

from ._init import server_init
from ._traefik import server_init_traefik, server_restart_traefik
from ._deploy import server_deploy, get_deploy_generator
from ._auth import get_public_key
from ._daemon import server_restart_daemon
from ._stats import server_restart_stats
from ._reboot import server_schedule_reboot
