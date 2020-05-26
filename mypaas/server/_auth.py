import os
import time

from ..utils import PublicKey

import toml


server_key_filename = "~/_mypaas/authorized_keys"
config_filename = "~/_mypaas/config.toml"

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
        _authorized_keys.update(get_authorized_keys(server_key_filename))

    return _authorized_keys.get(fingerprint, None)


def get_authorized_keys(filename):
    """ Read the authorized public keys from the file system.
    Returns a dict of PublicKey objects.
    """
    if filename.startswith("~"):
        filename = os.path.expanduser(filename)
    if not os.path.isfile(filename):
        return {}

    with open(filename, "rb") as f:
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


def load_config():
    """ Load config from disk.
    """
    filename = os.path.expanduser(config_filename)
    try:
        with open(filename, "rb") as f:
            return toml.loads(f.read().decode())
    except Exception:
        return {"init": {}, "env": {}}


def save_config(config):
    """ Save config to disk.
    """
    filename = os.path.expanduser(config_filename)
    with open(filename, "wb") as f:
        f.write(toml.dumps(config).encode())
