import os
import io
import zipfile
from urllib.parse import quote

import requests

from ._keys import get_private_key
from ..utils import generate_uid


def push(domain, directory):
    """ Push the given directory to your PaaS, where it will be
    deployed as an app/service. The directory must contain at least a
    Dockerfile.
    """

    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1]
    base_url = "https://" + domain.rstrip("/") + "/daemon"

    directory = os.path.abspath(directory)

    # Some checks
    if not os.path.isdir(directory):
        raise RuntimeError(f"Not a directory: {directory!r}")
    elif not os.path.isfile(os.path.join(directory, "Dockerfile")):
        raise RuntimeError(f"No Dockerfile found in {directory!r}")

    # Get the client's private key, used to sign the payload
    private_key = get_private_key()

    # Get the server's time.
    # The verify=True checks the cert (default True, but let's be explicit).
    r = requests.get(base_url + "/time", verify=True)
    if r.status_code != 200:
        raise RuntimeError("Could not get server time: " + r.text)
    server_time = int(r.text)

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
    payload = f.getvalue()

    # Compose a nice little token, and a signature for it that can only be
    # produced with the private key. The public key can verify this signature
    # to confirm that we have the private key.
    fingerprint = private_key.get_id()
    token = str(server_time) + "-" + generate_uid()
    sig1 = private_key.sign(token.encode())
    sig2 = private_key.sign(payload)

    # POST to the deploy server
    url = base_url + f"/push?id={fingerprint}&token={token}"
    url += f"&sig1={quote(sig1)}&sig2={quote(sig2)}"
    print(f"Pushing ...")
    r = requests.post(url, data=payload, stream=True, verify=True)
    if r.status_code != 200:
        raise RuntimeError("Push failed: " + r.text)
    else:
        for line in r.iter_lines():
            if isinstance(line, bytes):
                line = line.decode(errors="ignore")
            print(line)
