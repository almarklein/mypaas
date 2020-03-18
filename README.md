# MyPaas

MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, and offers free
automatic https and deployments via dockerfiles.

**DISCLAIMER: none of what is described below actually works yet - this document is what I'd want MyPaas to do.**

## Docker plus Traefik is awesome

[Docker](https://en.wikipedia.org/wiki/Docker_(software)) makes it
possible to run multiple applications on a single server in a contained
way, and setting (memory and CPU) limits on each container.

[Traefik](https://traefik.io/) is a modern router, reverse proxy, and
load balancer that can be automatically configured using labels on
Docker containers. It can also act as an https endpoint and
automatically refreshes SSL/TLS certificates with [Let's Encrypt](https://letsencrypt.org/).

[MyPaas](https://github.com/almarklein/mypaas) is no more than a tool
that helps you setup Traefik, and deploy Docker containers that have
the right labels so that Traefik handles them in the right way.


## How it works

MyPaas is a command line utility that you use both on your server (the PAAS),
as well as on other machines to push deploys to your server. There is no
web UI. You configure your service by adding special comments to the Dockerfile.


## Setting expectations

MyPaas is not for everyone. But if you like the command line, know how
to connect to a server with SSH, can edit files over SSH, and understand
the basics of Docker and systemctl, then you might really like it!


## Getting started

Login to your server via SSH. First, you'll need to install some
dependencies. We'll be assuming a fresh Ubuntu VM - you may need to
adjust the commands if you are using another operating system. You may
also need to add `sudo` in front of the commands.

First, let's make sure the package manager is up to date:
```
server$ apt update
```

Next, install Docker, start the service, and make sure it starts automatically after a reboot:
```
server$ apt install docker.io
server$ systemctl start docker
server$ systemctl enable docker
```

Now install MyPaas. It is written in Python, so we can use pip to install it (you'll need Python 3.6 or higher).
```
server$ apt install python3-pip
server$ pip3 install mypaas[server]
```

That's it, you can now initialize your server:
```
server$ mypaas init
```

The `init` command will:
* Start Traefik in a Docker container and make sure it is configured correctly.
* Start the mypaas deamon that can accept deployments from the client.

Your server is now a PAAS, ready to run apps and services!


## Setting up credentials

Before you can connect your client to your PAAS, you need to authenticate it.

MyPaas works with RSA key pairs. This means that there is a private key on
your device, which must be kept secret. This key is also encrypted with a
password for an extra layer of security. The corresponding public key is
added to a list at the server. The server uses the public key to confirm that
the client is who it claims to be. This key is public, you can safely email it
to somewhere (or post it on-line, if you want). Read more here (TODO).

To setup your keypair, run the following command (you can also re-use an existing key):
```
client$ mypaas key-init
```

The server needs your public key to be able to authenticate you.
Copy the public key to your clipboard:
```
client$ mypaas key-get
```

Then go back to your server and add the public key to the
`~/_mypaas/authorized_keys` file. You can add multiple public keys to
your server to allow access for multiple devices / developers.


## Deploying an app / service

In MyPaas, the unit of deployment is called a "service". These are
sometimes called "apps". Each service is defined using one Dockerfile,
resulting in one Docker image, and will be deployed as one or more
containers (more than one when scaling).

The service can be configured by adding special comments in the Dockerfile. For example:
```Dockerfile
# mypaas.service=hello-world
# mypaas.url=https://example.com
# mypaas.url=https://www.example.com

FROM python:3.8-slim-buster

RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1

WORKDIR /root
COPY . .
CMD python server.py
```

You can make a deployment by pushing the Dockerfile (and all other files in the
it's directory) to the server:
```
$ mypaas push myservername directory
```

The server will extract the files and then do a `mypaas server-deploy`. For the above example,
your service will now be available via `https://www.example.com` and `https://example.com.`
Don't forget that you need to point the domains' DNS records to the IP address of the server!


## CLI commands

```
$ mypaas init    # Initializes a server to use MyPaas deployment using Traefik and Docker.
                 # You'll typically only use this only once per server.
$ mypaas push    # Do a deploy from your workstation.
$ mypaas status  # Check on the status of the PAAS.
```

(there will probably be a few more commands)


## Configuration options

### mypaas.service

The name of the service. On each deploy, any service with the same name
will be replaced by the new deployment. It will also be the name of the
Docker image, and part of the name of the docker container. Therefore you can
eaily find it back using common Docker tools.

### mypaas.url

This specifies a domain, plus optional path for which the service want to
handle the requests. The url must start with either `http://` or `https://`,
specifying whether the connection must be secure or not.

Secure connections are recommended. Traefik will generate certificates
(via Let's Encrypt) and force all requests to be encrypted. Traefik
will also automatically renew the certificates before they expire.

You can use this parameter multiple times to specify multiple domains.
If no domains are specified, the service is not accessible from the outside,
but can still be used by other services (e.g. a database).

Examples:

* "http://example.com": unsecure connection
* "https://example.com": secure connection
* "https://foo.example.com": subdomain
* "https://foo.example.com/bar": paths

### mypaas.volume

Equivalent to Docker's `--volume` option. Enables mounting a specific
directory of the server in the Docker container, to store data that is
retained between reboots. E.g. `~/dir_or_root:/dir_on_container`.
Can be used multiple times to specify multiple mounted directories.

Note that any data stored inside a container that is not in a mounted
directory will be lost after a re-deploy or reboot.

### mypaas.port

The port that the process inside the container is listening on. Default 80.

### mypaas.scale

An integer specifying how many containers should be running for this service.
Can be set to 0 to indicate "non-scaling", which is the default.

When deploying a non-scaling service, the old container is stopped
before starting the new one, resulting in a downtime of around 5
seconds. This way, there is no risk of multiple containers writing to
the same data at the same time.

If `scaling` is given and larger than zero (so also when 1), a
deployment will have no downtime, because the new containers will be
started and given time to start up before the old containers are
stopped.
