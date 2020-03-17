import subprocess


def server_schedule_reboot(when="Sun 06:00:00"):
    """ Create a timer+service to reboot the server at a regular interval,
    e.g. every sunday. The default value for when is "Sun 06:00:00".
    """
    timer = mypaas_reboot_timer.replace("WHEN", when)
    service = mypaas_reboot_service

    with open("/etc/systemd/system/mypaas_reboot.timer", "bw") as f:
        f.write(timer.encode())
    with open("/etc/systemd/system/mypaas_reboot.service", "bw") as f:
        f.write(service.encode())

    subprocess.run(["systemctl", "start", "mypaas_reboot.timer"])
    subprocess.run(["systemctl", "enable", "mypaas_reboot.timer"])


mypaas_reboot_timer = """

[Unit]
Description=MyPaas reboot timer

[Timer]
OnCalendar=WHEN

[Install]
WantedBy=timers.target
"""

mypaas_reboot_service = """
[Unit]
Description=MyPaas reboot service

[Service]
User=root
ExecStart=reboot now
RestartSec=20
"""
