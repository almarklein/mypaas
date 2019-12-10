"""
MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.
"""

# flake8: noqa


__version__ = "0.1.0"
__traefik_version__ = "2.0.4"


# For use on server
from ._init import server_init
from ._deploy import server_deploy
from ._credentials import user_add, user_list, user_remove
from ._traefik import server_restart_traefik

# For use on remote system
from ._credentials import key_init, key_get, key_create
from ._push import push
from ._status import status
