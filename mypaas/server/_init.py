import os
import time
import json
import subprocess

from ._traefik import server_init_traefik, server_restart_traefik
from ._auth import server_key_filename


def server_init():
    """ Initialize the current machine to be a PAAS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """

    config = _collect_info_for_config()

    # Write config to file
    config_filename = os.path.expanduser("~/_mypaas/config.json")
    os.makedirs(os.path.dirname(config_filename), exist_ok=True)
    with open(config_filename, "wb") as f:
        f.write(json.dumps(config, indent=4).encode())

    # Make sure the keyfile is there
    print()
    filename = os.path.expanduser(server_key_filename)
    if os.path.isfile(filename):
        print(f"Leaving {filename} as it is.")
    else:
        print(f"Creating {filename}")
        with open(filename, "wb"):
            pass

    # Boot Traefik container
    print()
    print("Initializing Traefik (as a Docker container)")
    server_init_traefik()
    server_restart_traefik()

    # Boot stats container
    print()
    print("Initializing Stats server (as a Docker container)")
    server_restart_stats()

    # Boot daemon service
    print()
    print("Initializing MyPaas daemon (as a systemctl service)")
    server_restart_daemon()

    print()
    print("Your server is now ready!")


def _collect_info_for_config():
    """ Ask questions and return a config dict.
    """

    print()
    print("MyPaas needs a domain name that will be used for")
    print("the dashboard, API endpoint, monitoring, etc.")
    print("This can be e.g. paas.mydomain.com, or admin.mydomain.com")
    print("Note that you must point the DNS record to this server.")
    domain = input("Domain for this PAAS: ")
    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1].strip()

    print()
    print("Traefik will use Let's Encrypt to get SSL/TSL certificates.")
    print("Let's Encrypt can send an email when something is wrong.")
    email = input("Email for Let's Encrypt (optional): ").strip()

    return {"domain": domain, "email": email}
