import os
import time
import subprocess

from ._traefik import server_init_traefik, server_restart_traefik
from ._auth import server_key_filename


def server_init():
    """ Initialize the current machine to be a PAAS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """

    print()
    print("MyPaas needs a domain name that will be used for")
    print("the dashboard, API endpoint, monitoring, etc.")
    print("This can be e.g. paas.mydomain.com, or admin.mydomain.com")
    print("Note that you must point the DNS record to this server.")
    domain = input("Domain for this PAAS: ")
    if domain.lower().startswith(("https://", "http://")):
        domain = domain.split("//", 1)[-1]

    print()
    print("Traefik will use Let's Encrypt to get SSL/TSL certificates.")
    print("Let's Encrypt can send an email when something is wrong.")
    email = input("Email for Let's Encrypt (optional): ")

    print()
    print("Initializing Traefik")
    server_init_traefik(domain, email)
    server_restart_traefik()

    print()
    filename = os.path.expanduser(server_key_filename)
    if os.path.isfile(filename):
        print(f"Leaving {filename} as it is.")
    else:
        print(f"Creating {filename}")
        with open(filename, "wb"):
            pass

    print()
    print("Initialize MyPaas daemon service")
    server_restart_daemon()

    print()
    print("Your server is now ready!")


def server_restart_daemon():
    """ Restart the mypaas daemon.
    """
    filename = "/etc/systemd/system/mypaasd.service"
    with open(filename, "bw") as f:
        f.write(service.encode())
    time.sleep(0.1)
    try:
        subprocess.check_call(["systemctl", "daemon-reload"])
        subprocess.check_call(["systemctl", "restart", "mypaasd"])
        subprocess.check_call(["systemctl", "enable", "mypaasd"])
    except subprocess.SubprocessError:
        exit("Could not create mypaas daemon service")


service = """
[Unit]
Description=MyPaas daemon
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/python3 -m mypaas.server.daemon
RestartSec=2

[Install]
WantedBy=multi-user.target
"""
