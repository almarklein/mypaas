"""
MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.
"""

# flake8: noqa


__version__ = "0.1.0"
__traefik_version__ = "2.0.4"


# For use on server
from ._init import init
from ._deploy import deploy
from ._credentials import add_user
from ._traefik import restart_traefik

# For use on remote system
from ._credentials import add_server
from ._push import push
from ._status import status
