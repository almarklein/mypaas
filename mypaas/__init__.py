"""
MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.
"""

# flake8: noqa


__version__ = "0.2.0"
__traefik_version__ = "2.1.6"

version_info = tuple(map(int, __version__.split(".")))

from . import utils
from . import server
from . import client
