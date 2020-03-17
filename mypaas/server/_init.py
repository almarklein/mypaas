import os

from ._traefik import server_init_traefik, server_restart_traefik


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
    print("Initialize MyPaas daemon service")
    filename = "/etc/systemd/system/mypaasd.service"
    with open(filename, "bw") as f:
        f.write(service.encode())
    os.execl("systemctl", "start", "mypaasd.service")
    os.execl("systemctl", "enable", "mypaasd.service")

    print()
    print("Your server is now ready!")


service = """
[Unit]
Description=MyPaas daemon
After=network.target
RestartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
User=root
WorkingDirectory=/root
ExecStart=python3 -m mypaas.server.daemon
RestartSec=2

[Install]
WantedBy=multi-user.target
"""


mypaas_reboot_timer = """

[Unit]
Description=MyPaas reboot timer

[timer]
OnCalendar=Sun 06:00:00

[Install]
WantedBy=timers.target
"""

mypaas_reboot_srvice = """
[Unit]
Description=MyPaas reboot service

[Service]
User=root
ExecStart=reboot now
RestartSec=20
"""
