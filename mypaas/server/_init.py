import os
import sys
import time
import getpass
import subprocess

from ._traefik import init_router, restart_router
from ._stats import restart_stats
from ._daemon import restart_daemon
from ._auth import server_key_filename, load_config, save_config
from ..utils import dockercall


def init():
    """Initialize the current machine to be a PaaS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """

    print("\n    Hi, welcome to MyPaas!\n")
    time.sleep(1)

    # Load config
    config = load_config()

    print("----- Collecting info ".ljust(80, "-"))
    config["init"] = _collect_info_for_config()

    print("----- Preparing the system ".ljust(80, "-"))

    # Ensure that the root mypaas dir exists
    os.makedirs(os.path.expanduser("~/_mypaas"), exist_ok=True)

    # Write config file
    print("Saving MyPaas configuration")
    config["env"] = config.get("env", {}) or {"EXAMPLE_SECRET": "foobar"}
    save_config(config)

    # Make sure the keyfile is there
    pubkeys_filename = os.path.expanduser(server_key_filename)
    if os.path.isfile(pubkeys_filename):
        print(f"Leaving {pubkeys_filename} (containing public keys) as it is.")
    else:
        print(f"Creating {pubkeys_filename} (for public keys)")
        with open(pubkeys_filename, "wb"):
            pass

    # Make sure the keyfile is there
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

    print("----- Done ".ljust(80, "-"))
    print("MyPaas is ready to go.")
    print("Run 'mypaas server restart all' to start your PaaS")
    print()


def _collect_info_for_config():
    """Ask questions and return a config dict."""

    print()
    print("MyPaas needs a domain name that will be used for the API endpoint")
    print("and the dashboard. This can be e.g. admin.mydomain.com")
    print("Note that you must point the DNS record to the IP of this server.")
    print()
    domain = input("    Admin domain for this PaaS: ")
    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1].strip()

    print()
    print("The dashboard will be protected with a username and password.")
    print()
    username = input("    username: ")
    pw = getpass.getpass(f"    password: ")
    pwhash = _get_password_hash(pw)

    print()
    print("The Traefik router uses Let's Encrypt to get SSL/TSL certificates.")
    print("Let's Encrypt can send an email when something is wrong.")
    print()
    email = input("    Email for Let's Encrypt (optional): ").strip()

    print()
    print("Traefik can use different key types for SSL/TLS certificates.")
    key_types = ['EC256', 'EC384', 'RSA2048', 'RSA4096', 'RSA8192']
    print(f"Key Types: {key_types}")
    # https://wiki.mozilla.org/Security/Server_Side_TLS#Intermediate_compatibility_.28recommended.29
    print("Mozilla recommends EC256; some old clients (IE on Windows XP) only support RSA")
    print("EC uses far less CPU than RSA; Traefik defaults to RSA4096 for compatibility")
    key_type = input("    SSL/TLS Key Type: ").strip("' ")
    if key_type not in key_types:
        sys.exit(f"Invalid Key Type: {key_type}")
    print()

    return {"domain": domain, "web_credentials": f"{username}:{pwhash}", "email": email, "key_type": key_type}


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
    """Restart one or all of the MyPaas core processes.
    * all: restart router, stats server, and daemon.
    * daemon: restart the deploy daemon.
    * router: restart the Traefik router, e.g. after editing it's config.
    * stats: restart the stats server.
    """
    what = what.lower()

    if what == "all":
        what = "router stats daemon"
    whats = what.split()
    restarted_some = False

    if "daemon" in whats:
        print()
        print("----- (re)starting MyPaas daemon (as a systemctl service)")
        restart_daemon()
        restarted_some = True

    if "router" in whats:
        print()
        print("----- (re)starting Traefik router (as a Docker container)")
        restart_router()
        restarted_some = True

    if "stats" in whats:
        print()
        print("----- (re)starting stats server (as a Docker container)")
        restart_stats()
        restarted_some = True

    if not restarted_some:
        sys.exit(f"Invalid restart argument: {what}")
