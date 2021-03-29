"""
The code to deploy a service specified in a Dockerfile.
"""

import os
import time
import json
from urllib.parse import urlparse

from ..utils import dockercall
from ._auth import load_config


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
    """Make sure that the given name is clean,
    replacing invalid characters with a dash.
    """
    ok = identifier_chars + allowed_chars
    newname = "".join(c if c in ok else "-" for c in name)
    newname = newname.lstrip("-")
    if not newname:
        raise RuntimeError(f"No valid chars in name '{name}'.")
    return newname


def deploy(deploy_dir):
    """Deploy the current directory as a service. The directory must
    contain at least a Dockerfile. In most cases you should probably
    'mypaas push' from your work machine instead.
    """
    for step in get_deploy_generator(deploy_dir):
        print(step)


def get_deploy_generator(deploy_dir):
    """Get a generator that does the deploy, one step at a time, yielding
    a desciption of each step.
    """

    dockerfile = os.path.join(deploy_dir, "Dockerfile")

    # Get env-vars (e.g. secrets) from config
    config = load_config()
    secrets = config.get("env", {})

    # Init
    stripchars = "'\" \t\r\n"
    service_name = ""
    port = 80
    portmaps = []
    scale = None
    scale_option = "roll"
    urls = []
    volumes = []
    envvars = {}
    maxcpu = None
    maxmem = None
    healthcheck = None

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
                    for opt in ("safe", "roll"):
                        if opt in val:
                            scale_option = opt
                            val = val.replace(opt, "").strip()
                    scale = int(val)
                elif key == "mypaas.healthcheck":
                    parts = val.split()
                    if len(parts) != 3:
                        raise ValueError("Healthcheck must be /path interval timeout")
                    elif not parts[0].startswith("/"):
                        raise ValueError("Healthcheck path must start with '/'")
                    elif not parts[1].endswith(("ms", "s", "m" "h")):
                        raise ValueError(
                            "Healthcheck interval must be a durarion ending in 'ms', 's', 'm' or 'h'"
                        )
                    elif not parts[2].endswith(("ms", "s", "m" "h")):
                        raise ValueError(
                            "Healthcheck timeout must be a durarion ending in 'ms', 's', 'm' or 'h'"
                        )
                    healthcheck = {
                        "path": parts[0],
                        "interval": parts[1],
                        "timeout": parts[2],
                    }
                elif key == "mypaas.env":
                    val = val.strip()
                    if "=" in val:
                        k, _, v = val.partition("=")
                    elif val in secrets:
                        k, v = val, secrets[val]
                    else:
                        raise ValueError(
                            f"Env {val} is not found in ~/_mypaas/config.toml"
                        )
                    envvars[k.strip()] = v.strip()
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

    # Get clean names
    service_name = clean_name(service_name, ".-/")  # suited for an env var
    traefik_service_name = clean_name(service_name, "").rstrip("-") + "-service"
    traefik_service = f"traefik.http.services.{traefik_service_name}"

    # Collect info from all containers. Note that names can change but labels cannot.
    container_infos = get_containers_info(service_name)

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
        label(f"traefik.enable=true")
        label(f"{traefik_service}.loadbalancer.server.port={port}")
        if healthcheck and scale and scale > 0:
            # Turning on the health check ensures that the load balancer won't use
            # the container until the server actually runs.
            label(
                f"{traefik_service}.loadbalancer.healthCheck.path={healthcheck['path']}"
            )
            label(
                f"{traefik_service}.loadbalancer.healthCheck.interval={healthcheck['interval']}"
            )
            label(
                f"{traefik_service}.loadbalancer.healthCheck.timeout={healthcheck['timeout']}"
            )
    for url in urls:
        router_name = clean_name(url.netloc + url.path, "").strip("-") + "-router"
        router_insec = router_name.rpartition("-")[0] + "-https-redirect"
        rule = f"Host(`{url.netloc}`)"
        if len(url.path) > 0:  # single slash is no path
            rule += f" && PathPrefix(`{url.path}`)"
        # Make sure that this rule is not also used in another service, otherwise
        # the URL will not work, and it may also disturb other rules for this service.
        for info in container_infos:
            if info["is_this_service"]:
                continue
            if any(rule == value for value in info["labels"].values()):
                raise ValueError(
                    f"URL {url.netloc + url.path} is already used in {info['name']}"
                )
        if url.scheme == "https":
            # Secure
            label(f"traefik.http.routers.{router_name}.rule={rule}")
            label(f"traefik.http.routers.{router_name}.entrypoints=web-secure")
            label(f"traefik.http.routers.{router_name}.tls.certresolver=default")
            label(f"traefik.http.routers.{router_name}.tls.options=intermediate@file")
            label(f"traefik.http.routers.{router_name}.middlewares=hsts-header@file")
            # Redirect
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
        server_dir, _, container_dir = volume.partition(":")
        if server_dir.startswith("~"):
            server_dir = os.path.expanduser(server_dir)
        server_dir = os.path.realpath(server_dir)
        if not server_dir.startswith(os.path.expanduser("~")):
            raise ValueError(f"Cannot map a volume onto {server_dir}")
        elif any(server_dir.startswith(d) for d in FORBIDDEN_DIRS):
            raise ValueError(f"Cannot map a volume onto {server_dir}")
        os.makedirs(server_dir, exist_ok=True)
        cmd.append(f"--volume={server_dir}:{container_dir}")

    # Set user env vars
    for k, v in envvars.items():
        cmd.append(f"--env={k}={v}")

    # Set some env variables
    cmd.append(f"--env=MYPAAS_SERVICE={service_name}")
    cmd.append(f"--env=MYPAAS_SCALE={scale}")
    cmd.append(f"--env=MYPAAS_PORT={port}")
    # --env=MYPAAS_CONTAINER is set in the functions below.

    # Deploy!
    if scale and scale > 0:
        if scale_option == "roll":
            return _deploy_scale_roll(
                container_infos, deploy_dir, service_name, cmd, scale
            )
        else:
            return _deploy_scale_safe(
                container_infos, deploy_dir, service_name, cmd, scale
            )
    else:
        return _deploy_no_scale(container_infos, deploy_dir, service_name, cmd)


def _deploy_no_scale(container_infos, deploy_dir, service_name, prepared_cmd):
    image_name = clean_name(service_name, ".-:/")
    base_container_name = clean_name(image_name, ".-")
    new_name = f"{base_container_name}"

    yield ""
    yield f"deploying {service_name} to container {new_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "--pull", "-t", image_name, deploy_dir)

    # There typically is one, but there may be more, if we had failed
    # deploys or if previously deployed with scale > 1
    old_ids = get_id_name_for_this_service(container_infos)
    unique = str(int(time.time()))

    yield f"renaming {len(old_ids)} container(s)"
    for i, id in enumerate(old_ids.keys()):
        try:
            dockercall("rename", id, base_container_name + f".old.{unique}.{i+1}")
        except Exception:
            yield "Rename failed. Probably a crashed container -> removing!"
            dockercall("rm", "-f", id, fail_ok=True)

    for id, name in old_ids.items():
        yield f"stopping container (was {name})"
        dockercall("stop", id, fail_ok=True)

    try:
        yield f"starting new container {new_name}"
        cmd = prepared_cmd.copy()
        cmd.append(f"--env=MYPAAS_CONTAINER={new_name}")
        cmd.extend([f"--name={new_name}", image_name])
        dockercall(*cmd)
    except Exception:
        yield "fail -> recovering"
        dockercall("rm", "-f", new_name, fail_ok=True)
        for id, name in old_ids.items():
            dockercall("rename", id, name, fail_ok=True)
            dockercall("start", id, fail_ok=True)
        raise
    else:
        yield f"removing {len(old_ids)} old container(s)"
        for id in old_ids.keys():
            dockercall("rm", id, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {service_name}"


def _deploy_scale_safe(container_infos, deploy_dir, service_name, prepared_cmd, scale):
    image_name = clean_name(service_name, ".-:/")
    base_container_name = clean_name(image_name, ".-")

    yield ""
    yield f"deploying {service_name} to containers {base_container_name}.1..{scale}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "--pull", "-t", image_name, deploy_dir)

    old_ids = get_id_name_for_this_service(container_infos)
    unique = str(int(time.time()))

    yield f"renaming {len(old_ids)} current containers"
    for i, id in enumerate(old_ids.keys()):
        try:
            dockercall("rename", id, base_container_name + f".old.{unique}.{i+1}")
        except Exception:
            yield "Rename failed. Probably a crashed container -> removing!"
            dockercall("rm", "-f", id, fail_ok=True)

    for id, name in old_ids.items():
        yield f"stopping container (was {name})"
        dockercall("stop", id, fail_ok=True)

    # Keep track of started containers, in case we must shut them down
    new_pool = []

    try:
        for i in range(scale):
            new_name = f"{base_container_name}.{i+1}"
            yield f"starting new container {new_name}"
            new_pool.append(new_name)
            cmd = prepared_cmd.copy()
            cmd.append(f"--env=MYPAAS_CONTAINER={new_name}")
            cmd.extend([f"--name={new_name}", image_name])
            dockercall(*cmd)
    except Exception:
        yield "fail -> recovering"
        for name in new_pool:
            dockercall("stop", name, fail_ok=True)
            dockercall("rm", name, fail_ok=True)
        for id, name in old_ids.items():
            dockercall("rename", id, name, fail_ok=True)
            dockercall("start", id, fail_ok=True)
        raise
    else:
        yield f"removing {len(old_ids)} old containers"
        for id in old_ids.keys():
            dockercall("rm", id, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {service_name}"


def _deploy_scale_roll(container_infos, deploy_dir, service_name, prepared_cmd, scale):
    image_name = clean_name(service_name, ".-:/")
    base_container_name = clean_name(image_name, ".-")

    yield ""
    yield f"rolling deploy of {service_name} to containers {base_container_name}.1..{scale}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "--pull", "-t", image_name, deploy_dir)

    old_ids = get_id_name_for_this_service(container_infos)
    unique = str(int(time.time()))

    yield f"renaming {len(old_ids)} current containers (and wait 2s)"
    for i, id in enumerate(old_ids.keys()):
        try:
            dockercall("rename", id, base_container_name + f".old.{unique}.{i+1}")
        except Exception:
            yield "Rename failed. Probably a crashed container -> removing!"
            dockercall("rm", "-f", id, fail_ok=True)

    # Give things a bit of time to settle
    time.sleep(2)

    # Prepare pools
    old_pool = list(old_ids.keys())  # we pop and stop containers from this pool
    new_pool = []  # we add started containers to this pool

    # Determine how long to wait each time before stopping an old container,
    # based on the assumption that a container boots within 5 seconds.
    # In essence, we dont want to close the last old container before the first
    # new container is fully operational.
    max_time_we_expect_a_container_to_boot = 5
    pause_per_step = 1 + max_time_we_expect_a_container_to_boot / max(1, len(old_pool))

    try:
        for i in range(scale):
            # Start up a new container
            new_name = f"{base_container_name}.{i+1}"
            yield f"starting new container {new_name} (and wait {pause_per_step:0.1f}s)"
            new_pool.append(new_name)
            cmd = prepared_cmd.copy()
            cmd.append(f"--env=MYPAAS_CONTAINER={new_name}")
            cmd.extend([f"--name={new_name}", image_name])
            dockercall(*cmd)
            # Stop a container from the pool
            if old_pool:
                time.sleep(pause_per_step)
                id = old_pool.pop(0)
                yield f"stopping old container (was {old_ids[id]})"
                dockercall("stop", id, fail_ok=True)
                time.sleep(0.5)  # Again give it time to settle
    except Exception:
        yield "fail -> recovering"
        for name in new_pool:
            dockercall("stop", name, fail_ok=True)
            dockercall("rm", name, fail_ok=True)
        for id, name in old_ids.items():
            dockercall("rename", id, name, fail_ok=True)
            if id not in old_pool:
                dockercall("start", id, fail_ok=True)
        raise
    else:
        for id in old_pool:
            yield f"stopping old container (was {old_ids[id]})"
            dockercall("stop", id, fail_ok=True)
        yield f"removing {len(old_ids)} old containers"
        for id in old_ids.keys():
            dockercall("rm", id, fail_ok=True)

    yield "pruning"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {service_name}"


def get_id_name_for_this_service(container_infos):
    """Get a dict mapping id->name for all containers corresponding to the
    current service.
    """
    ids = []
    for info in container_infos:
        if info["is_this_service"]:
            ids.append((info["name"], info["id"]))  # name first, for sorting
    ids.sort()
    return {id: name for name, id in ids}


def get_containers_info(service_name):
    """Get a list of dicts with info on each currently running container."""
    # Get current container ids
    ids = dockercall("container", "ls", "--format", "{{.ID}}").split()
    # Get info for each container
    container_infos = []
    for id in ids:
        name_json = dockercall(
            "inspect", "--format", "{{.Name}}@{{json .Config.Labels}}", id
        )
        name, json_str = name_json.split("@", 1)
        container_infos.append(
            {"id": id, "name": name.lstrip("/"), "labels": json.loads(json_str)}
        )
    # Mark containers that match our service name
    base_container_name = clean_name(service_name, ".-")
    container_prefix = base_container_name + "."
    for info in container_infos:
        name = info["name"]
        is_this = name == base_container_name or name.startswith(container_prefix)
        info["is_this_service"] = is_this
    return container_infos
