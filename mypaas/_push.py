import os
import io
import getpass
import zipfile
from urllib.parse import quote

import requests

# from ._credentials import load_credentials_at_user


def push(domain, directory):
    """ Push the given directory to your PAAS, where it will be
    deployed as an app/service. The directory must contain at least a
    Dockerfile.
    """

    # Some checks
    if not os.path.isdir(directory):
        raise RuntimeError(f"Not a directory: {directory!r}")
    elif not os.path.isfile(os.path.join(directory, "Dockerfile")):
        raise RuntimeError(f"No Dockerfile found in {directory!r}")

    # Get key for this machine
    try:
        key1 = load_credentials_at_user()[domain]
    except KeyError:
        raise RuntimeError(f"No key for {domain}, first use mypaas add-server")

    # Get ket for user
    key2 = getpass.getpass(f"Passphrase: ")

    # Zip it up
    print("Zipping up ...")
    f = io.BytesIO()
    with zipfile.ZipFile(f, "w") as zf:
        for root, dirs, files in os.walk(directory):
            if "__pycache__" in root or "htmlcov" in root:
                continue
            for fname in files:
                filename = os.path.join(root, fname)
                zf.write(filename, os.path.relpath(filename, directory))

    # POST to the deploy server
    url = f"https://{domain}/push?key1={key1}&key2={quote(key2)}"
    print(f"Pushing ...")
    r = requests.post(url, data=f.getvalue(), stream=True)
    if r.status_code != 200:
        raise RuntimeError("Push failed: " + r.text)
    else:
        for line in r.iter_lines():
            if isinstance(line, bytes):
                line = line.decode(errors="ignore")
            print(line)
