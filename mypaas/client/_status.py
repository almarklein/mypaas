from urllib.parse import quote

import requests

from ._keys import get_private_key
from ..utils import generate_uid


def status(domain):
    """ View status of containers. CPU, memory, mounts, labels, etc.  Note that
    this feature is somewhat experimental, and the returned info may change.
    """

    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1]
    base_url = "https://" + domain.rstrip("/")

    # Get the server's time
    r = requests.get(base_url + "/time")
    if r.status_code != 200:
        raise RuntimeError("Could not get server time: " + r.text)
    server_time = int(r.text)

    # Compose a nice little token, and a signature for it that can only be
    # produced with the private key. The public key can verify this signature
    # to confirm that we have the private key.
    private_key = get_private_key()
    token = server_time + "-" + private_key.get_id() + "-" + generate_uid()
    signature = private_key.sign(token)

    # GET from the deploy server
    url = base_url + f"/status?token={token}&signature={quote(signature)}"
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        raise RuntimeError("Getting status failed: " + r.text)
    else:
        for line in r.iter_lines():
            if isinstance(line, bytes):
                line = line.decode(errors="ignore")
            print(line)
