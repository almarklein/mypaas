import os
import sys
import json
import getpass
import subprocess

from ._traefik import init_router, restart_router
from ._stats import restart_stats
from ._daemon import restart_daemon
from ._auth import server_key_filename
from ..utils import dockercall


def init():
    """ Initialize the current machine to be a PaaS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """
    config = _collect_info_for_config()
    print("-" * 80)

    # Ensure that the root mypaas dir exists
    os.makedirs(os.path.expanduser("~/_mypaas"), exist_ok=True)

    # Write config file
    print("Saving MyPaas configuration")
    config_filename = os.path.expanduser("~/_mypaas/config.json")
    with open(config_filename, "wb") as f:
        f.write(json.dumps(config, indent=4).encode())

    # Make sure the keyfile is there
    print()
    pubkeys_filename = os.path.expanduser(server_key_filename)
    if os.path.isfile(pubkeys_filename):
        print(f"Leaving {pubkeys_filename} (containing public keys) as it is.")
    else:
        print(f"Creating {pubkeys_filename} (for public keys)")
        with open(pubkeys_filename, "wb"):
            pass

    # Create Docker network
    print("Creating Docker network 'mypaas-net'")
    dockercall("network", "create", "mypaas-net", fail_ok=True)

    # Traefik also needs to so some setup
    init_router()

    print("-" * 80)
    print("MyPaas is ready to go.")
    print("Run 'mypaas server restart all' to start your PaaS")


def _collect_info_for_config():
    """ Ask questions and return a config dict.
    """

    print()
    print("MyPaas needs a domain name that will be used for")
    print("the dashboard, API endpoint, monitoring, etc.")
    print("This can be e.g. paas.mydomain.com, or admin.mydomain.com")
    print("Note that you must point the DNS record to this server.")
    domain = input("Admin domain for this PaaS: ")
    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1].strip()

    print()
    print("The web pages to view status and analytics are protected")
    print("a username and password.")
    username = input("username: ")
    pw = getpass.getpass(f"Password: ")
    pwhash = _get_password_hash(pw)

    print()
    print("Traefik will use Let's Encrypt to get SSL/TSL certificates.")
    print("Let's Encrypt can send an email when something is wrong.")
    email = input("Email for Let's Encrypt (optional): ").strip()

    return {"domain": domain, "web_credentials": f"{username}:{pwhash}", "email": email}


def _get_password_hash(pw):
    p = subprocess.Popen(
        ["openssl", "passwd", "-apr1", "-stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    p.stdin.write(pw.encode() + b"\n")
    hash, _ = p.communicate()
    return hash.decode().strip()


def restart(what):
    """ Restart one or all of the MyPaas core processes.
    * all: restart router, stats server, and daemon.
    * router: restart the Traefik router, e.g. after editing it's config.
    * stats: restart the stats server.
    * daemon: restart the deploy daemon.
    """
    what = what.lower()

    if what == "all":
        whats = "router stats daemon"
    whats = what.split()
    restarted_some = False

    if "router" in whats:
        print()
        print("(re)starting Traefik router (as a Docker container)")
        restart_router()
        restarted_some = True

    if "stats" in whats:
        print()
        print("re)starting stats server (as a Docker container)")
        restart_stats()
        restarted_some = True

    if "daemon" in whats:
        print()
        print("re)starting MyPaas daemon (as a systemctl service)")
        restart_daemon()
        restarted_some = True

    if not restarted_some:
        sys.exit(f"Invalid restart argument: {what}")
