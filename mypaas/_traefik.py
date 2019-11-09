import os

from . import __traefik_version__
from ._utils import dockercall


def restart_traefik():
    """ Restart the Traefik docker container. You can run this after
    updating the config (~/_traefik/traefik.toml or staticroutes.toml)
    or to update Traefik after updating MyPaas. Your PAAS will be
    offline for a few seconds.
    """

    image_name = "traefik:" + __traefik_version__

    print(f"Pulling Docker image: {image_name}")
    dockercall("pull", image_name)

    print("Stopping and removing current Traefik container (ignore errors)")
    dockercall("stop", "traefik", fail_ok=True)
    dockercall("rm", "traefik", fail_ok=True)

    print("Launching new Traefik container")
    cmd = ["run", "-d", "--restart=always"]
    cmd.extend(["--network=mypaas-net", "--ports=80:80", "--ports=443:443"])
    cmd.append("--volume=/var/run/docker.sock:/var/run/docker.sock")
    cmd.append("--volume=~/_traefik/traefik.toml:/traefik.toml")
    cmd.append("--volume=~/_traefik/acme.json:/acme.json")
    cmd.append("--volume=~/_traefik/staticroutes.toml:/staticroutes.toml")
    cmd.extend(["--name=traefik", image_name])
    dockercall(*cmd)


def init_traefik(email, dashboard_domain):
    """ Prepare the system for running Traefik (Docker network and config).
    """

    # Create docker network
    dockercall("network", "create", "mypaas-net", fail_ok=True)

    # Make sure that the server has a dir for Traefik to store stuff
    traefik_dir = os.path.expanduser("~/_traefik")
    os.makedirs(traefik_dir, exist_ok=True)

    # Make sure there is an acme.json with the right permissions
    if not os.path.isfile(os.path.join(traefik_dir, "acme.json")):
        with open(os.path.join(traefik_dir, "acme.json"), "wb"):
            pass
    os.chmod(os.path.join(traefik_dir, "acme.json"), 600)

    # Create the static config
    text = traefik_config.replace("EMAIL", email)
    with open(os.path.join(traefik_dir, "traefik.toml"), "wb") as f:
        f.write(text.encode())

    # Create the file-provider's config
    text = traefik_staticroutes.replace(
        "TRAEFIK_DASHBOARD_DOMAIN", dashboard_domain
    )
    with open(os.path.join(traefik_dir, "staticroutes.toml"), "wb") as f:
        f.write(text.encode())


traefik_config = """
# Traefik config file
# https://docs.traefik.io/reference/static-configuration/file/

[log]
  level = "WARN"

# Define entrypoints: what ports Traefik listens on
[entryPoints]
  [entryPoints.http]
    address = ":80"
  [entryPoints.https]
    address = ":443"

# Define providers for dynamic config. We use Docker and a file
[providers.docker]
  endpoint = "unix:///var/run/docker.sock"
  network = "mypaas-net"
  watch = true
  exposedByDefault = false
  useBindPortIP = false
[providers.file]
  filename = "/staticroutes.toml"

# Enable dashboard
[api]
  dashboard = true

# Enable Let's Encrypt
[certificatesResolvers.default.acme]
  email = "EMAIL"
  storage = "acme.json"
  [certificatesResolvers.default.acme.httpchallenge]
    entrypoint = "http"
""".lstrip()


# todo: use a secret path instead of username + pw ?
# todo: ssl
traefik_staticroutes = """
[http.routers.api]
  rule = "Host(`TRAEFIK_DASHBOARD_DOMAIN`)"
  entrypoints = ["http", "https"]
  service = "api@internal"
  #middlewares = ["auth"]

[http.middlewares.auth.basicAuth]
  users = [
    "admin:your-password-hash"
  ]
""".lstrip()
