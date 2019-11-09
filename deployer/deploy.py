import sys
import time
import subprocess

if len(sys.argv) <= 1:
    dockerfile = "Dockerfile"
elif len(sys.argv) == 2:
    dockerfile = sys.argv[1]
else:
    raise SystemExit("Usage: mypaas deploy [dockerfile]")


stripchars = "'\" \t\r\n"
image_name = ""
port = 80
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
                elif key == "mypaas.imagename":
                    image_name = val
                elif key == "mypaas.domain":
                    domains.append(val)
                elif key == "mypaas.volume":
                    volumes.append(val)
                elif key == "mypaas.port":
                    port = int(val)
                else:
                    raise ValueError(f"Invalid mypaas deploy option: {key}")

# We meed at least an image name
if not image_name:
    raise ValueError(
        "No image name given. Use '# mypaas.imagename=xxxx' in the Dockerfile."
    )

# Get container name(s)
container_name = image_name.replace(":", "-")
alt_container_name = container_name + "-old"


# Construct command to start the container
cmd = ["docker", "run", "-d", "--restart=always"]
if domains:
    cmd.append(f"--label=traefik.enable=true")
    cmd.append(f"--network=mypaas-net")
    # cmd.append(f'--label=traefik.port={port}')
    # cmd.append(f'--label="traefik.docker.network=mypaas-net"')
for domain in domains:
    router_name = domain.replace(".", "_") + "-router"
    service_name = container_name + "-service"
    # router_name = container_name  # remove this!!
    cmd.append(
        f"--label=traefik.http.routers.{router_name}.rule=Host(`{domain}`, `www.almarklein.com`)"
    )
    # cmd.append(f'--label="traefik.http.routers.{router_name}.service={service_name}"')
    # cmd.append(f'--label="traefik.http.routers.{router_name}.tls=true"')
    cmd.append(f"--label=traefik.http.routers.{router_name}.entrypoints=http")
    cmd.append(
        f"--label=traefik.http.services.{service_name}.loadbalancer.server.port={port}"
    )
    # cmd.append(f'--label="traefik.http.routers.{router_name}.tls.certresolver=default"')
    # cmd.append(f'--label="traefik.http.middlewares.xxxxxxxxx.redirectscheme.scheme=https"')
for volume in volumes:
    cmd.append(f"--volume={volume}")

# Add environment variable to identify the image from within itself
# cmd.append(f"--env=DDEPLOY_CONTAINER_NAME={container_name}")
# Finalize the deploy script
cmd.append(f"--name={container_name}")
cmd.append(image_name)


# Deploy!
# cmd = " ".join(cmd)
print(" ".join(cmd))

print(f"mypaas deploy: deploying {image_name} to container {container_name}")
time.sleep(1)

print("========== building image")
subprocess.check_call(["docker", "build", "-t", image_name, "."])

print("========== renaming current")
subprocess.call(["docker", "rename", container_name, alt_container_name])

try:
    print("========== starting new container")
    subprocess.call(["docker", "stop", container_name])
    subprocess.call(["docker", "rm", container_name])
    subprocess.check_call(cmd)
except Exception as err:
    # Rename back
    subprocess.call(["docker", "rename", alt_container_name, container_name])
    raise err
else:
    time.sleep(5)  # Give it time to start up
    print("========== stopping old container")
    subprocess.call(["docker", "stop", alt_container_name])
    subprocess.call(["docker", "rm", alt_container_name])


print(f"========== Done deploying {container_name}")
