"""
The mypaas.client subpackage contains the logic for the commands to run at the client.

Dependencies: pyperclip, requests
"""

# flake8: noqa

from ._keys import key_init, key_gen, key_get
from ._push import push
