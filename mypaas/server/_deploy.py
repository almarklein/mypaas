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
    maxcpu = None
    maxmem = None

    # Get configuration from dockerfile
    with open(dockerfile, "rt", encoding="utf-8") as f:
        for line in f.readlines():
            if not line.lstrip().startswith("#"):
                continue
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
                elif key == "mypaas.maxcpu":
                    maxcpu = str(float(val))
                elif key == "mypaas.maxmem":
                    assert all(c in "0123456789kmgtKMGT" for c in val)
                    maxmem = val
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

    # Apply limits
    if maxcpu:
        cmd.append(f"--cpus=" + maxcpu)
    if maxmem:
        cmd.append(f"--memory=" + maxmem)

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
        # The stats server needs to be behind auth
        if service_name == "stats":
            label(f"traefik.http.routers.{router_name}.middlewares=auth@file")

    for volume in volumes:
        server_dir = volume.split(":")[0]
        if server_dir.startswith("~"):
            server_dir = os.path.expanduser(server_dir)
        server_dir = os.path.realpath(server_dir)
        if not server_dir.startswith(os.path.expanduser("~")):
            raise ValueError(f"Cannot map a volume onto {server_dir}")
        elif any(server_dir.startswith(d) for d in FORBIDDEN_DIRS):
            raise ValueError(f"Cannot map a volume onto {server_dir}")
        os.makedirs(server_dir, exist_ok=True)
        cmd.append(f"--volume={volume}")

    # Add environment variable to identify the image from within itself
    cmd.append(f"--env=MYPAAS_SERVICE_NAME={service_name}")

    # cmd only needs ["--name={container_name}", f"{image_name}"]

    # Deploy!
    if scale and scale > 0:
        return _deploy_scale(deploy_dir, image_name, cmd, scale)
    else:
        return _deploy_no_scale(deploy_dir, image_name, cmd)


def _deploy_no_scale(deploy_dir, image_name, prepared_cmd):
    container_name = clean_name(image_name, ".-")

    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, deploy_dir)

    # There typically is one, but there may be more, if we had failed
    # deploys or if previously deployed with scale > 1
    old_ids = get_ids_from_container_name(container_name)

    yield "renaming current container(s)"
    for i, id in enumerate(old_ids.keys()):
        dockercall("rename", id, container_name + ".old.{i+1}", fail_ok=True)

    yield "stopping old container(s)"
    for id in old_ids.keys():
        dockercall("stop", id, fail_ok=True)

    try:
        yield "starting new container"
        cmd = prepared_cmd + [f"--name={container_name}", image_name]
        dockercall(*cmd)
    except Exception:
        yield "fail -> recovering"
        dockercall("rm", container_name, fail_ok=True)
        for id, name in old_ids.items():
            dockercall("start", id, fail_ok=True)
            dockercall("rename", id, name, fail_ok=True)
        raise
    else:
        for id in old_ids.keys():
            dockercall("rm", id, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {image_name}"


def _deploy_scale(deploy_dir, image_name, prepared_cmd, scale):
    container_name = clean_name(image_name, ".-")

    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, deploy_dir)

    old_ids = get_ids_from_container_name(container_name)

    yield "renaming current containers"
    for i, id in enumerate(old_ids.keys()):
        dockercall("rename", id, container_name + ".old.{i+1}", fail_ok=True)

    new_names = []
    try:
        yield "starting new containers (and give them time to start up)"
        for i in range(scale):
            new_name = f"{container_name}.{i+1}"
            cmd = prepared_cmd + [f"--name={new_name}", image_name]
            dockercall(*cmd)
            new_names.append(new_name)
    except Exception:
        yield "fail -> recovering"
        for name in new_names:
            dockercall("stop", name, fail_ok=True)
            dockercall("rm", name, fail_ok=True)
        for id, name in old_ids.items():
            dockercall("rename", id, name, fail_ok=True)
        raise
    else:
        time.sleep(5)  # Give it time to start up
        yield "stopping old containers"
        for id in old_ids.keys():
            dockercall("stop", id, fail_ok=True)
            dockercall("rm", id, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {image_name}"


def get_ids_from_container_name(container_name):
    """ Get a dict mapping container id to name,
    for each container that matches the given name.
    """
    container_prefix = container_name + "."
    lines = dockercall("ps", "-a").splitlines()
    ids = []
    for line in lines[1:]:
        parts = line.strip().split()
        id = parts[0]
        name = parts[-1]
        if name == container_name or name.startswith(container_prefix):
            ids.append((name, id))  # name first, for sorting
    ids.sort()
    return {id: name for name, id in ids}
