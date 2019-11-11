import getpass
from urllib.parse import quote

import requests

from ._credentials import load_credentials_at_user


def stats(domain):
    """ View stats
    """

    # Get key for this machine
    try:
        key1 = load_credentials_at_user()[domain]
    except KeyError:
        raise RuntimeError(f"No key for {domain}, first use mypaas add-server")

    # Get ket for user
    key2 = getpass.getpass(f"Passphrase: ")

    # POST to the deploy server
    # todo: HTTPS!!
    url = f"http://{domain}/stats?key1={key1}&key2={quote(key2)}"
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        raise RuntimeError("Getting stats failed: " + r.text)
    else:
        for line in r.iter_lines():
            if isinstance(line, bytes):
                line = line.decode(errors="ignore")
            print(line)
