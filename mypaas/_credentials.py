import os
import json
import getpass

import pyperclip

from ._utils import USER_CONFIG_DIR, SERVER_CONFIG_DIR, yesorno
from ._crypto import PrivateKey, PublicKey


# todo: how auth could work:

# ## Using custom key-pairs and an http API:
# server has endpoint that shows its current time
# client queries that to detect any time offset, then does queries
# each query contains a JWT-like token that makes claim on the public key id
# and the time. The token is signed with the private key.
# The server tests whether the time is between 5 s from now and now.
# The server validates whether the claimed public key can indeed verify the signing.
# The token is put in a list/queue so it cannot be used again, where it must be at least 5 s.
#
# ## Using SSH (via paramiko):
# public keys are added to .ssh/authorized_keys
# client connects via SSH and simply does it thing
# no need for an http API on the paas: much simpler
# the only downside is that anyone with the key has root access to the server
# this is most problematic for the key that we set at CI/CD, because we have less control over it

# %% on the server


def user_add(name, key):
    """ Register a user's public key. The name can be anything to identify
    the key by, e.g. "John Doe" or "Gitlab-CD".
    """
    # Check args
    if not (isinstance(key, str) and key.startswith("rsa-pub-")):
        raise TypeError("public key must be a string starting with rsa-pub-'")
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    if "<" in name or ">" in name:
        raise ValueError("Invalid characters in name, replace <name> with an actual name.")

    # Get keys and add
    keys = get_the_public_keys()
    if name in keys:
        if not yesorno(f"A public key for {name} already exists. Overwrite? (y/n)> "):
            return
    keys[name] = PublicKey.from_str(key)

    # Write back
    set_the_public_keys(keys)
    print(f"Public key stored for {name}. There are now {len(keys)} keys.")


def user_list():
    """ List all public keys.
    """
    for name, key in get_the_public_keys().items():
        print(f"{name} ({key.get_id()})")


def user_remove(name):
    """ Remove the public key corresponding to the given name.
    """
    keys = get_the_public_keys()

    if name not in keys:
        print(f"No public key found for {name}")
        return
    elif not yesorno(f"Remove the public key of {name}? (y/n)> "):
        return

    keys.pop(name)
    set_the_public_keys(keys)


def get_the_public_keys():

    filename = os.path.join(SERVER_CONFIG_DIR, "public_keys.txt")
    if not os.path.isfile(filename):
        return {}

    with open(filename, "rb") as f:
        text = f.read().decode()

    keys = {}
    for line in text.splitlines():
        name, _, key = line.strip().rpartition(" ")
        if not key.startswith("rsa-pub-"):
            continue
        try:
            keys[name] = PublicKey.from_str(key)
        except Exception as err:
            print(f"Invalid key {name}: {str(err)}")

    return keys


def set_the_public_keys(keys):
    lines = [f"{name} {key.to_str()}" for name, key in keys.items()]
    text = "\n".join(lines)

    filename = os.path.join(SERVER_CONFIG_DIR, "public_keys.txt")
    with open(filename, "wb") as f:
        f.write(text.encode())


# %% on the client

remote_text = """
So you are going to store the key somewhere else, like on CI/CD. It's
important to keep this key secret: store it in a safe place and nowhere else.
You can always create a new key if needed.
""".strip()

public_text = """
The public key is not a secret. You can share it if you want. It can be used to
confirm that you have the private key. The public key is now on the clipboard.
SSH into your paas server and run:

    mypaas add_user <name> <pubic_key>

""".strip()


def key_init():
    """ Create a keypair to authorize access of this machine to a MyPaas server.
    The private key is stored on this machine and should be kept secret. You
    can use the same key to authorize access to multiple servers.
    """
    # Where to store our rsa private key
    filename = os.path.join(USER_CONFIG_DIR, "key.rsa")
    has_key = os.path.isfile(filename)

    # Generate keypair
    private_key = PrivateKey.generate()
    public_key = private_key.get_public_key()
    print("A new keypair has been generated ...")

    # Store private key
    print("\n========== Store the private key on this machine")
    if has_key:
        if not yesorno("A key is already present, overwrite? (y/n)> "):
            return
    print("It is strongly recommended to protect your key with a passprase.")
    pp = getpass.getpass("Your passphrase to protect key: ")
    with open(filename, "wb") as f:
        f.write(private_key.to_str(pp).encode())
    print("Your private key is now stored on this machine.")

    # Copy public key
    print("\n========== Put the public key at the server")
    _show_public_key(public_key)


def key_create():
    """ Create a keypair to authorize access to a MyPaas server. The private key
    is not stored on this machine, but should be copied to where it's needed
    (e.g. the secret environment variables in your CI/CD).
    """
    # Where to store our rsa private key
    filename = os.path.join(USER_CONFIG_DIR, "key.rsa")
    has_key = os.path.isfile(filename)

    # Generate keypair
    private_key = PrivateKey.generate()
    public_key = private_key.get_public_key()
    print("A new keypair has been generated ...")

    # Copy private key
    print("\n========== Store the private key somewhere else")
    print("")
    print(remote_text)
    print("")
    input("Hit enter to copy the key to the clipboard. > ")
    pyperclip.copy(private_key.to_str(None).replace("\n", "_"))
    try:
        print("Now paste the key to its desitnation, ")
        input("and hit enter again to clear the clipboard. > ")
    finally:
        pyperclip.copy("")

    # Copy public key
    print("\n========== Put the public key at the server")
    _show_public_key(public_key)


def key_get():
    """ Get the public key corresponding to the private key of this machine.
    This key can be shared. The key will be copied to the clipboard.
    """

    # Where to store our rsa private key
    filename = os.path.join(USER_CONFIG_DIR, "key.rsa")
    if not os.path.isfile(filename):
        raise RuntimeError("No key present yet. Create a keypair first.")

    # Load key
    with open(filename, "rb") as f:
        s = f.read().decode()

    pp = getpass.getpass("Your key's passphrase: ")
    private_key = PrivateKey.from_str(s, pp)
    public_key = private_key.get_public_key()

    _show_public_key(public_key)


def _show_public_key(public_key):
    pyperclip.copy(public_key.to_str())
    print(public_text.replace("<pubic_key>", f"...{public_key.get_id()}"))


# def load_credentials_at_server():
#     filename = os.path.join(SERVER_CONFIG_DIR, "user_credentials.json")
#     try:
#         with open(filename, "rb") as f:
#             credentials = json.loads(f.read().decode())
#     except (FileNotFoundError, json.JSONDecodeError):
#         credentials = {}
#     return credentials
#
#
# def load_credentials_at_user():
#     filename = os.path.join(USER_CONFIG_DIR, "server_credentials.json")
#     try:
#         with open(filename, "rb") as f:
#             credentials = json.loads(f.read().decode())
#     except (FileNotFoundError, json.JSONDecodeError):
#         credentials = {}
#     return credentials
#
#
# def hash_key(key):
#     return hashlib.sha256(key.encode()).hexdigest()
