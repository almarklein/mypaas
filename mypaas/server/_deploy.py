"""
The code to deploy a service specified in a Dockerfile.
"""

import os
import time
from urllib.parse import urlparse

from ..utils import dockercall


alphabet = "abcdefghijklmnopqrstuvwxyz"
identifier_chars = alphabet + alphabet.upper() + "0123456789" + "_"

# Cannot map a volume onto these
FORBIDDEN_DIRS = [
    "~/.ssh",
    "~/_mypaas",
]
for d in list(FORBIDDEN_DIRS):
    if d.startswith("~"):
        FORBIDDEN_DIRS.append(os.path.expanduser(d))


def clean_name(name, allowed_chars):
    """ Make sure that the given name is clean,
    replacing invalid characters with a dash.
    """
    ok = identifier_chars + allowed_chars
    newname = "".join(c if c in ok else "-" for c in name)
    newname = newname.lstrip("-")
    if not newname:
        raise RuntimeError(f"No valid chars in name '{name}'.")
    return newname


def deploy(deploy_dir):
    """ Deploy the current directory as a service. The directory must
    contain at least a Dockerfile. In most cases you should probably
    'mypaas push' from your work machine instead.
    """
    for step in get_deploy_generator(deploy_dir):
        print(step)


def get_deploy_generator(deploy_dir):
    """ Get a generator that does the deploy, one step at a time, yielding
    a desciption of each step.
    """

    dockerfile = os.path.join(deploy_dir, "Dockerfile")

    stripchars = "'\" \t\r\n"
    service_name = ""
    port = 80
    portmaps = []
    scale = None
    urls = []
    volumes = []

    # Get configuration from dockerfile
    with open(dockerfile, "rt", encoding="utf-8") as f:
        for line in f.readlines():
            if "#mypaas." in line or " mypaas." in line:
                line = line.lstrip("# \t")
                if line.startswith("mypaas."):
                    key, _, val = line.partition("=")
                    key = key.strip(stripchars)
                    val = val.strip(stripchars)

                    if not val:
                        pass
                    elif key == "mypaas.service":
                        service_name = val
                    elif key == "mypaas.url":
                        url = urlparse(val)
                        if url.scheme not in ("http", "https") or not url.netloc:
                            raise ValueError("Invalid mypaas.url: {val}")
                        elif url.params or url.query or url.fragment:
                            raise ValueError("Too precise mypaas.url: {val}")
                        urls.append(url)
                    elif key == "mypaas.volume":
                        volumes.append(val)
                    elif key == "mypaas.port":
                        port = int(val)
                    elif key == "mypaas.publish":
                        portmaps.append(val)
                    elif key == "mypaas.scale":
                        scale = int(val)
                        if scale > 1:
                            raise NotImplementedError("scale >1 not yet implemented")
                    else:
                        raise ValueError(f"Invalid mypaas deploy option: {key}")

    # We need at least an image name
    if not service_name:
        raise ValueError(
            "No service name given. Use '# mypaas.service=xxxx' in Dockerfile."
        )

    # Get container name(s)
    image_name = clean_name(service_name, ".-:/")
    traefik_service_name = clean_name(image_name, "").rstrip("-") + "-service"
    traefik_service = f"traefik.http.services.{traefik_service_name}"

    def label(x):
        cmd.append("--label=" + x)

    # Construct command to start the container
    cmd = ["run", "-d", "--restart=always"]

    # Always use mypaas network, so services find each-other by container name.
    cmd.append(f"--network=mypaas-net")

    # Add portmappings to local system
    cmd.extend(["--publish=" + portmap for portmap in portmaps])

    if urls:
        cmd.append(f"--label=traefik.enable=true")
    for url in urls:
        label(f"{traefik_service}.loadbalancer.server.port={port}")
        router_name = clean_name(url.netloc + url.path, "").strip("-") + "-router"
        router_insec = router_name.rpartition("-")[0] + "-https-redirect"
        rule = f"Host(`{url.netloc}`)"
        if len(url.path) > 0:  # single slash is no path
            rule += f" && PathPrefix(`{url.path}`)"
            # mn = f"{image_name}-pathstrip"  # middleware name
            # label(f"traefik.http.middlewares.{mn}.stripprefix.prefixes={url.path}")
            # label(f"traefik.http.routers.{router_name}.middlewares={mn}")
        if url.scheme == "https":
            label(f"traefik.http.routers.{router_name}.rule={rule}")
            label(f"traefik.http.routers.{router_name}.entrypoints=web-secure")
            label(f"traefik.http.routers.{router_name}.tls.certresolver=default")
            label(f"traefik.http.routers.{router_insec}.rule={rule}")
            label(f"traefik.http.routers.{router_insec}.entrypoints=web")
            label(
                f"traefik.http.routers.{router_insec}.middlewares=https-redirect@file"
            )
        else:
            label(f"traefik.http.routers.{router_name}.rule={rule}")
            label(f"traefik.http.routers.{router_name}.entrypoints=web")
        # The stats server needs to be begind auth
        if service_name == "stats":
            label(f"traefik.http.routers.{router_name}.middlewares=auth@file")

    for volume in volumes:
        server_dir = volume.split(":")[0]
        if server_dir.lower() in FORBIDDEN_DIRS:
            raise ValueError(f"Cannot map a volume onto {server_dir}")
        os.makedirs(server_dir, exist_ok=True)
        cmd.append(f"--volume={volume}")

    # Netdata requires some more priveleges
    # if service_name == "netdata": HACK
    #     cmd.extend(["--cap-add", "SYS_PTRACE", "--security-opt", "apparmor=unconfined"])

    # Add environment variable to identify the image from within itself
    cmd.append(f"--env=MYPAAS_SERVICE_NAME={service_name}")

    # cmd only needs ["--name={container_name}", f"{image_name}"]

    # Deploy!
    if scale and scale > 0:
        return _deploy_scale(deploy_dir, image_name, cmd, scale)
    else:
        return _deploy_no_scale(deploy_dir, image_name, cmd)


def _deploy_no_scale(deploy_dir, image_name, cmd):
    container_name = clean_name(image_name, ".-")
    alt_container_name = container_name + "-old"

    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, deploy_dir)

    yield "renaming current"
    dockercall("rm", alt_container_name, fail_ok=True)
    dockercall("rename", container_name, alt_container_name, fail_ok=True)

    yield "stopping old container"
    dockercall("stop", alt_container_name, fail_ok=True)

    try:
        yield "starting new container"
        cmd.extend([f"--name={container_name}", image_name])
        dockercall(*cmd)
    except Exception:
        yield "fail -> recovering"
        dockercall("start", alt_container_name, fail_ok=True)
        dockercall("rm", container_name, fail_ok=True)
        dockercall("rename", alt_container_name, container_name, fail_ok=True)
        raise
    else:
        dockercall("rm", alt_container_name, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {image_name}"


def _deploy_scale(deploy_dir, image_name, cmd, scale):
    container_name = clean_name(image_name, ".-")
    alt_container_name = container_name + "-old"

    # todo: scale > 1

    # Deploy!
    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, deploy_dir)

    yield "renaming current"
    dockercall("rm", alt_container_name, fail_ok=True)
    dockercall("rename", container_name, alt_container_name, fail_ok=True)

    try:
        yield "starting new container (and give it time to start up)"
        dockercall("stop", container_name, fail_ok=True)
        dockercall("rm", container_name, fail_ok=True)
        cmd.extend([f"--name={container_name}", image_name])
        dockercall(*cmd)
    except Exception:
        # Rename back
        yield "fail -> recovering"
        dockercall("rename", alt_container_name, container_name, fail_ok=True)
        raise
    else:
        time.sleep(5)  # Give it time to start up
        yield "stopping old container"
        dockercall("stop", alt_container_name, fail_ok=True)
        dockercall("rm", alt_container_name, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {image_name}"
