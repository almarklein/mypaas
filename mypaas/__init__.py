"""
MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.
"""

# flake8: noqa


__version__ = "0.2.0"
__traefik_version__ = "2.1.6"

version_info = tuple(map(int, __version__.split(".")))


from .server import (
    server_init,
    server_init_traefik,
    server_restart_daemon,
    server_restart_traefik,
    server_restart_stats,
    server_deploy,
    server_schedule_reboot,
)
from .client import key_init, key_gen, key_get, push, status
