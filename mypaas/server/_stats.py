import os
import json
import shutil

from ._deploy import deploy  # noqa


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
STATS_LIB_DIR = os.path.join(os.path.dirname(THIS_DIR), "stats")


def restart_stats():
    """ Restart the stats server.
    """

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
        deploy(deploy_dir)
    finally:
        shutil.rmtree(deploy_dir, ignore_errors=True)


DOCKERFILE = """
# mypaas.service=stats
# mypaas.url=https://PAAS_DOMAIN/
# mypaas.port=80
# mypaas.publish=127.0.0.1:8125:8125/udp
# mypaas.volume=/root/_stats:/root/_stats
# mypaas.scale=0

FROM ubuntu:20.04

RUN apt update \
    && apt install python3-psutil \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1 pscript fastuaparser

WORKDIR /root
COPY . .
CMD python -m stats
""".lstrip()
