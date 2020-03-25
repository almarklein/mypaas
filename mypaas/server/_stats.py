import os
import shutil

from . import server_deploy  # noqa


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
STATS_LIB_DIR = os.path.join(os.path.dirname(THIS_DIR), "stats")


DOCKERFILE = """
# mypaas.service=stats
# mypaas.url=https://PAAS_DOMAIN/stats
# mypaas.port=80
# mypaas.publish=127.0.0.1:8125:8125/udp
# mypaas.scale=0

FROM python:3.8-slim-buster

RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1 pscript psutil

WORKDIR /root
COPY . .
CMD python server.py
""".lstrip()


def server_restart_stats():

    # Get config
    config_filename = os.path.expanduser("~/_mypaas/config.json")
    with open(config_filename, "rb") as f:
        config = json.loads(f.read().decode())

    deploy_dir = os.path.expanduser("~/_mypaas/stats_deploy_cache")
    dockerfile = DOCKERFILE.replace("PAAS_DOMAIN", config["domain"])

    try:
        # Put required files in deploy dir
        shutil.rmtree(deploy_dir, ignore_errors=True)
        shutil.copytree(STATS_LIB_DIR, os.path.join(deploy_dir, "stats"))
        with open(os.path.join(deploy_dir, "Dockerfile"), "wb") as f:
            f.write(dockerfile.encode())
        # Deploy
        server_deploy(deploy_dir)
    finally:
        shutil.rmtree(deploy_dir, ignore_errors=True)
