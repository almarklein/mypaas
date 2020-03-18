import os
import time

from ..utils import PublicKey

server_key_filename = "~/_mypaas/authorized_keys"

last_key_read = 0
_authorized_keys = {}


def get_public_key(fingerprint):
    """ Get the public key for the given fingerprint
    """
    # Read the keys from the filesystem at most once each few seconds,
    # to prevent attacks on the auth service.
    global last_key_read
    if last_key_read < time.time() - 5:
        last_key_read = time.time()
        _authorized_keys.clear()
        _authorized_keys.update(get_authorized_keys())

    return _authorized_keys.get(fingerprint, None)


def get_authorized_keys():
    """ Read the authorized public keys from the file system.
    Returns a dict of PublicKey objects.
    """

    filename = os.path.expanduser(server_key_filename)
    if not os.path.isfile(filename):
        return {}

    with open(filename, "rb").read() as f:
        text = f.read().decode(errors="ignore")

    keys = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            key = PublicKey.from_str(line)
        except Exception:
            print(f"Does not look like a public key: {line}")
        else:
            keys[key.get_id()] = key
    return keys
