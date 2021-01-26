"""
MyPaas is a tool that makes it easy to run a platform as a service (PaaS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.
"""

# flake8: noqa


__version__ = "0.5.1"
__traefik_version__ = "2.3.7"

version_info = tuple(map(int, __version__.split(".")))

from . import utils
from . import server
from . import client
