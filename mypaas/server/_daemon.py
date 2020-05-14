import sys
import time
import subprocess


def restart_daemon():
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
        sys.exit("Could not create mypaas daemon service")


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
ExecStart=/usr/bin/python3 -m mypaas.daemon
RestartSec=2
Environment=MYPAAS_SERVICE=daemon
Environment=MYPAAS_CONTAINER=daemon

[Install]
WantedBy=multi-user.target
"""

# Note: the MYPAAS_CONTAINER is for the deamon's statsgen to
# discover this process and measure its CPU and ram.
