# MyPaas

MyPaas is a tool that makes it very easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, and offers free
automatic https and deployments via dockerfiles.

DISCLAIMER: none of what is described below actually works yet - this document is what I'd want MyPaas to do.

## Docker plus Traefik is awesome

Docker makes it possible to run multiple applications on a single server
in a contained way, and setting (memory and CPU) limits on each container.

Traefik is a fast and modern router, reverse proxy, and load balancer that be
automatically configured using labels on Docker containers. It can also acts
as an https endpoint and automatically refreshes ssl certificates with
Let's Encrypt.

MyPaas is no more than a tool that helps you setup Traefik, and makes it easy
to deploy docker containers that have the right labels so that Traefik handles
them in the right way.


## How it works

MyPaas is a command line utility that you use both on the target machine,
as well as on other machines to push deploys to your servers. There is no
web UI. The configuration of the services is listed as special comments
in the Dockerfile.


## Getting started

First, we'll need to install some dependencies. We'll be assuming a
fresh Ubuntu VM - you may need to asjust the commands if you are using
another operating system. You may also need to add `sudo` in front of
the commands.

First, let's make sure the package manager is up to date:
```
$ apt update
```

Next, install Docker, start the service, and make sure it starts automatically after a reboot:
```
$ apt install docker.io
$ systemctl start docker
$ systemctl enable docker
```

MyPaas is written in Python (you'll need Python 3.6 or higher). Let's install it!
```
$ apt install python3-pip
$ pip3 install mypaas
```

That's it, we can now initialize MyPaas!
```
$ mypaas init
```

The `init` command will:
* Start Traefik in a Docker container and make sure it is configured correctly
* Start a server (in a Docker container) that can accept deployments from the outside.
* Start a service (via systemctl) that will perform the deployments that the server prepares.

Your system is now ready!


## Setting up credentials

TODO


## Deploying a service

In MyPaas, any deployment is called a "service". These are also
sometimes called "apps". Each service is defined using one Dockerfile,
resulting in one Docker image, and will be deployed as one or more
containers (more than one when scaling).

The service can be configured by adding special comments in the Dockerfile. For example:
```
# mypaas.servicename = example-service
# mypaas.domain = www.mydomain.com
# mypaas.domain = mydomain.com

FROM python:3.7-alpine

RUN apk update
RUN pip --no-cache-dir install click h11 \
    && pip --no-cache-dir install uvicorn==0.6.1 --no-deps \
    && pip --no-cache-dir install asgineer==0.7.1

COPY . .
CMD python server.py
```

You can deploy services when logged into the machine running the paas using:
```
$ mypaas deploy Dockerfile
```

But in most cases, you'll be deploying from another machine by pushing the dockerfile
(and all other files in the current directory) to the server:
```
$ mypaas push myservername Dockerfile
```

The server will accept the files and then do a `mypaas deploy`. For the above example,
your service will now be available via http://www.mydomain.com and http://mydomain.com.
Note though, that you need to point the DNS records to the IP address of the server.


## CLI commands

```
$ mypaas init    # Initializes a server to use MyPaas deployment using Traefik and Docker.
                 # You'll typically only use this only once per server.
$ mypaas deploy  # Run on the server to deploy a service from a Dockerfile.
                 # Mosy users will probably use push instead.
$ mypaas push    # Do a deploy from another computer.

(there will probably be a few more commands)


## Configuration options

### mypaas.servicename

The name of the service. On each deploy, any service with the same name
will be replaced by the new deployment. It will also be the name of the
Docker image, and part of the name of the docker container. In that waym you can
eaily find it back using common Docker tools.

### mypaas.domain

Requests for this domain must be routed to this service, e.g.
`mydomain.com`, `foo.myname.org`, etc. You can use this parameter
multiple times to specify multiple domains.

If no domains are specified, the service is not accessible from the outside, but
can still be used by other services (e.g. a database).

### mypaas.https

A boolean ("true" or "false") indicating whether to enable `https`. Default `false`.
When `true`, Traefik will generate certificates and force all requests to be encrypted.

Before enabling this, make sure that all domains actually resolve to
the server, because Let's Encrypt limits the number of requests for a
certificate.

### mypaas.volume

Equivalent to Docker's `--volume` option. Enables mounting a specific
directory of the server in the Docker container, to store data that is
retained between reboots. E.g. `~/dir_or_root:/dir_on_container`.
Can be used multiple times to specify multiple mounted directories.

### mypaas.port

The port that the service is listening on. Default 80.

### mypaas.scale

An integer specifying how many containers should be running for this service.
Can be set to 0 to indicate "non-scaling", which is the default.

When deploying a non-scaling service, the old container is stopped
before starting the new one, resulting in a downtime of around 5
seconds.

If `scaling` is given and larger than zero (so also when scaling is set to 1),
a deployment will have no downtime, because the new containers will be
started and given time to start up before the old containers are stopped.

