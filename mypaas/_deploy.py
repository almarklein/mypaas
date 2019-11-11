import os
import time

from ._utils import dockercall


alphabet = "abcdefghijklmnopqrstuvwxyz"
identifier_chars = alphabet + alphabet.upper() + "0123456789" + "_"


def clean_name(name, allowed_chars):
    ok = identifier_chars + allowed_chars
    newname = "".join(c if c in ok else "-" for c in name)
    newname = newname.lstrip("-")
    if not newname:
        raise RuntimeError(f"No valid chars in name '{name}'.")
    return newname


def deploy(deploy_dir):
    """ Deploy the current directory as a service. The directory must
    contain at least a Dockerfile. You'll probably use push instead.
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
    scale = None
    domains = []
    volumes = []

    # Get configuration from dockerfile
    with open(dockerfile, "rt", encoding="utf-8") as f:
        for line in f.readlines():
            if "#mypaas." in line or " mypaas." in line:
                line = line.lstrip("# \t")
                if line.startswith("mypaas."):
                    key, _, val = line.partition("=")
                    val = val.strip(stripchars)

                    if not val:
                        pass
                    elif key == "mypaas.service":
                        service_name = val
                    elif key == "mypaas.domain":
                        domains.append(val)
                        # TODO: also allow routing on path?
                    elif key == "mypaas.volume":
                        volumes.append(val)
                    elif key == "mypaas.port":
                        port = int(val)
                    elif key == "mypaas.https":
                        raise NotImplementedError("https not yet implemented")
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
    if domains:
        cmd.append(f"--label=traefik.enable=true")
        cmd.append(f"--network=mypaas-net")
    for domain in domains:
        # todo: https
        # todo: combine inside rule
        # todo: also paths
        router_name = domain.replace(".", "_") + "-router"
        # router_name = container_name  # remove this!!
        label(f"traefik.http.routers.{router_name}.rule=Host(`{domain}`)")
        # label(f"traefik.http.routers.{router_name}.tls=true"')
        label(f"traefik.http.routers.{router_name}.entrypoints=web")
        label(f"{traefik_service}.loadbalancer.server.port={port}")
        # label(f"traefik.http.routers.{router_name}.tls.certresolver=default")
        # label(f"traefik.http.middlewares.xxxxxxx.redirectscheme.scheme=https")
    for volume in volumes:
        cmd.append(f"--volume={volume}")

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

    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, deploy_dir)

    yield "stopping old container"
    dockercall("stop", container_name, fail_ok=True)
    dockercall("rm", container_name, fail_ok=True)

    yield "starting new container"
    cmd.extend([f"--name={container_name}", image_name])
    dockercall(*cmd)

    yield "pruning\n"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield "done deploying {image_name}"


def _deploy_scale(deploy_dir, image_name, cmd, scale):
    container_name = clean_name(image_name, ".-")
    alt_container_name = container_name + "-old"

    # todo: scale > 1

    # Deploy!
    yield f"deploying {image_name} to container {container_name}"
    time.sleep(1)

    yield "building image"
    dockercall("build", "-t", image_name, ".")

    yield "renaming current"
    dockercall("rename", container_name, alt_container_name, fail_ok=True)

    try:
        yield "starting new container (and give time to start up)"
        dockercall("stop", container_name, fail_ok=True)
        dockercall("rm", container_name, fail_ok=True)
        cmd.extend([f"--name={container_name}", image_name])
        dockercall(*cmd)
    except Exception as err:
        # Rename back
        dockercall("rename", alt_container_name, container_name, fail_ok=True)
        raise err
    else:
        time.sleep(5)  # Give it time to start up
        yield "stopping old container"
        dockercall("stop", alt_container_name, fail_ok=True)
        dockercall("rm", alt_container_name, fail_ok=True)

    yield "pruning\n"
    dockercall("container", "prune", "--force")
    dockercall("image", "prune", "--force")
    yield f"done deploying {image_name}"
