import os

from .. import __traefik_version__
from ..utils import dockercall
from ._auth import load_config


# Notes:
# * Traefik checks whether the domain actually resolves to itself,
#   see disablepropagationcheck


def restart_router():
    """ Restart the Traefik docker container. You can run this after
    updating the config (~/_mypaas/traefik.toml or staticroutes.toml)
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
    traefik_dir = os.path.expanduser("~/_mypaas")
    cmd.extend(["--network=host", "-p=80:80", "-p=443:443"])
    cmd.append("--volume=/var/run/docker.sock:/var/run/docker.sock")
    cmd.append(f"--volume={traefik_dir}/traefik.toml:/traefik.toml")
    cmd.append(f"--volume={traefik_dir}/acme.json:/acme.json")
    cmd.append(f"--volume={traefik_dir}/staticroutes.toml:/staticroutes.toml")
    cmd.append(f"--env=MYPAAS_SERVICE=traefik")
    cmd.append(f"--env=MYPAAS_CONTAINER=traefik")
    cmd.extend(["--name=traefik", image_name])
    dockercall(*cmd)


def init_router():
    """
    Prepare the system for running Traefik (Docker network and config).
    Running this again will reset Traefik "to factory defaults".
    """

    # Get config
    traefik_dir = os.path.expanduser("~/_mypaas")
    config = load_config()

    # Make sure there is an acme.json with the right permissions
    acme_filename = os.path.join(traefik_dir, "acme.json")
    if os.path.isfile(acme_filename):
        print(f"Leaving {acme_filename} (containing certificates) as it is.")
    else:
        print(f"Creating {acme_filename} (for certificates)")
        with open(os.path.join(traefik_dir, "acme.json"), "wb"):
            pass
    os.chmod(os.path.join(traefik_dir, "acme.json"), 0o600)

    # Create the static config
    print("Writing Traefik config")
    text = traefik_config.replace("EMAIL", config["init"]["email"])
    with open(os.path.join(traefik_dir, "traefik.toml"), "wb") as f:
        f.write(text.encode())

    # Create the file-provider's config
    print("Writing Traefik static routes")
    text = traefik_staticroutes.replace("PAAS_DOMAIN", config["init"]["domain"])
    text = text.replace("WEB_CREDENTIALS", config["init"]["web_credentials"])
    with open(os.path.join(traefik_dir, "staticroutes.toml"), "wb") as f:
        f.write(text.encode())


traefik_config = """
# Traefik config file.
# Traefik must be restarted for changes to take effect.
# https://docs.traefik.io/reference/static-configuration/file/

[log]
  level = "WARN"

# Define entrypoints: what ports Traefik listens on
[entryPoints]
  [entryPoints.web]
    address = ":80"
  [entryPoints.web-secure]
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
  watch = true

# Enable dashboard
[api]
  dashboard = true

# Enable Let's Encrypt
[certificatesResolvers.default.acme]
  email = "EMAIL"
  storage = "acme.json"
  [certificatesResolvers.default.acme.httpchallenge]
    entrypoint = "web"

# Process metrics (use the influxDB protocol, because it sends aggregates)
[metrics]
  [metrics.influxDB]
    address = "127.0.0.1:8125"
    addEntryPointsLabels = false
    addServicesLabels = true
    pushInterval = "1s"

""".lstrip()


traefik_staticroutes = """
# Trafic config for statically defined routes and middleware.
# Traefik should update automatically when changed are made (without restart).

# The Traefik dashboard
[http.routers.api]
  rule = "Host(`PAAS_DOMAIN`) && (PathPrefix(`/dashboard`) || PathPrefix(`/api`))"
  entrypoints = ["web-secure"]
  service = "api@internal"
  middlewares = ["auth"]
  [http.routers.api.tls]
    certresolver = "default"

# The routing for mypaas daemon
[http.routers.mypaas-daemon-router]
  rule = "Host(`PAAS_DOMAIN`) && PathPrefix(`/daemon`)"
  entrypoints = ["web-secure"]
  service = "mypaas-daemon"
  [http.routers.mypaas-daemon-router.tls]
    certresolver = "default"
[http.services.mypaas-daemon.loadBalancer]
    [[http.services.mypaas-daemon.loadBalancer.servers]]
      url = "http://127.0.0.1:88"

[http.middlewares]
  [http.middlewares.https-redirect.redirectscheme]
    scheme = "https"

# You can update/add users here and then 'mypaas server restart traefik'
# Create a password hash using e.g. 'openssl passwd -apr1'
[http.middlewares.auth.basicAuth]
  users = ["WEB_CREDENTIALS"]

""".lstrip()
