"""
Code related to key pairs at the client.
"""

import os
import getpass

import pyperclip

from ..utils import input_ask_bool, input_ask_int, PrivateKey

standard_key_filename = os.path.normpath(os.path.expanduser("~/.ssh/id_rsa"))
default_key_filename = os.path.normpath(os.path.expanduser("~/.ssh/mypaas_rsa"))

os.makedirs(os.path.expanduser("~/.ssh"), exist_ok=True)

private_text = """
It's important to keep the private key secret: store it in a safe place
and nowhere else. You can always create a new key if needed.
""".strip()

public_text = """
The public key is used by the server to confirm that you have the
private key. You can safely share the public key; it is not a secret.
The public key is now on the clipboard. SSH into your paas server
and add it to ~/_mypaas/authorized_keys
""".rstrip()

OPTIONS = [
    f"0. Keep as it is",
    f"1. Generate a new RSA keypair (and store it in '{default_key_filename}')",
    f"2. Use an existing RSA key file",
    f"3. Use the standard RSA key '{standard_key_filename}'",
]


def get_key_filename_and_text():
    """ Get the filename that contains the RSA key, and the containing text.
    We use one specific file location, but it may point to another RSA file.
    """
    filename = default_key_filename

    if not os.path.isfile(filename):
        raise RuntimeError("RSA keyfile does not exist. Create a new keypair.")

    with open(filename, "rb") as f:
        text = f.read().decode().strip()

    if text.startswith("file://"):
        filename = text.split("//", 1)[-1]
        if not os.path.isfile(filename):
            raise RuntimeError(
                f"Referenced keyfile '{filename}' does not exist. Create new keypair."
            )
        with open(filename, "rb") as f:
            text = f.read().decode().strip()

    return filename, text


def key_init():
    """ Setup a keypair to authorize this machine to a MyPaas server.
    The private key is stored on this machine and should be kept secret.
    You can also choose to use an existing RSA key.
    """

    # Get current status
    try:
        filename, text = get_key_filename_and_text()
        status = f"Using RSA keyfile: '{filename}'"
        current_status_ok = True
    except RuntimeError as err:
        status = str(err)
        current_status_ok = False
    print("Current client status:\n    " + status)
    print()

    # Get options, and remove the ones that do not make sense.
    options = OPTIONS.copy()
    if not current_status_ok:
        options.pop(0)  # Doing nothing does not make sense when the state sucks
    if not os.path.isfile(standard_key_filename):
        options.pop(-1)  # Standard SSH file not there

    # Ask user what to do
    valid_choices = [int(option[0]) for option in options]
    choice = input_ask_int("\n".join(options) + "\nYour choice> ", valid_choices)

    if choice == 0:
        print("No action required.")
        return

    elif choice == 1:
        filename = default_key_filename
        # If there already is a key, we maybe should not overwrite it
        if os.path.isfile(filename) and current_status_ok:
            if not input_ask_bool(
                f"A key is already present at '{filename}'. Overwrite? (y/n)> "
            ):
                return
        # Generate the keypair
        print("\nGenerating keypair ... ", end="")
        private_key = PrivateKey.generate()
        print("Done.")
        # Store the private key, with a passphrase
        print("It is strongly recommended to protect your key with a passprase.")
        print("You'll be typing it in a lot; keep it simple (but not too short).")
        pp = getpass.getpass("Your passphrase to protect the key: ")
        with open(filename, "wb") as f:
            f.write(private_key.to_str(pp).encode())
        print(f"Your private key is now stored at '{filename}'.")

    elif choice == 2 or choice == 3:
        # Select and check filename
        if choice == 3:
            filename = standard_key_filename
        else:
            filename = input("Path to RSA file> ")
        if not os.path.isfile(filename):
            raise RuntimeError(f"File does not exist: '{filename}'")
        # Write the proxy
        with open(default_key_filename, "wb") as f:
            f.write(("file://" + filename).encode())
        print(f"Now using private key from '{filename}'.")

    else:
        raise RuntimeError("Woops, Don't know what to do.")  # should be unreachable


def key_gen():
    """
    Generate (but not store) a generic (passwordless) SSH keypair,
    e.g. to use in CI/CD.
    """

    # Generate the keypair
    print("\nGenerating keypair ... ", end="")
    private_key = PrivateKey.generate()
    public_key = private_key.get_public_key()
    print("Done.")

    # Copy private key
    print(private_text)
    print("")
    input("Hit enter to copy the private key to the clipboard. > ")
    pyperclip.copy(private_key.to_str(None).replace("\n", "_"))
    try:
        print("Now paste the key to its destnation, ")
        input("and then hit enter again to clear the clipboard. > ")
    finally:
        pyperclip.copy("")

    # Copy public key
    _show_public_key(public_key)


def key_get():
    """
    Get the public key corresponding to the private key on this machine.
    This public key can be shared. The key is printed and copied to the
    clipboard.
    """
    private_key = get_private_key()
    public_key = private_key.get_public_key()
    _show_public_key(public_key)


def get_private_key():
    """ Get the private key, so our commands like `push` can authenticate.
    """
    keyname = "MYPAAS_PRIVATE_KEY"

    if os.getenv(keyname, ""):
        text = os.environ[keyname]
        filename = keyname
        pp = ""
    else:
        filename, text = get_key_filename_and_text()
        pp = getpass.getpass(f"Passphrase for key '{filename}': ")

    try:
        return PrivateKey.from_str(text, pp)
    except Exception as err:
        raise RuntimeError(f"Could not load key from {filename}: {str(err)}")


def _show_public_key(public_key):
    pyperclip.copy(public_key.to_str())
    print(public_text)
    print("\nKeypair fingerprint: " + public_key.get_id())
