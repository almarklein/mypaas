# Deploying an app / service with MyPaas


## Defining a service

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
    && pip --no-cache-dir install asgineer

WORKDIR /root
COPY . .
CMD python server.py
```

To detect mypaas configuration options, the daemon detects whether a line starts with "#mypaas.",
allowing tabs and spaces right before and after the "#". To temporary comment
an option, you can e.g. write "#--- mypaas.url=".


## Pushing a deployment

You can make a deployment by pushing the Dockerfile (and all other files in
its directory) to the server:
```
$ mypaas push myservername directory
```

The server will extract the files and then do a `mypaas server deploy`.
This means that the Docker image will be build, and subsequently run
as a container. For the above example, your service will now be
available via `https://www.example.com` and `https://example.com.` Don't
forget that you need to point the domain's DNS records to the IP address
of the server!

In case you want to deploy a pre-built Docker image, your Dockerfile
will simply state `FROM registry.example.com/your/image:tag`.


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

### mypaas.env

Specify environment variables, e.g. "FOO=bar". If you only specify a key, that
value is sampled from the server config (the env section in `~/_mypaas/config.toml`).
That makes this a safe and convenient way to provide your apps with
secrets (e.g. API tokens).

### mypaas.port

The port that the process inside the container is listening on. Default 80.

### mypaas.publish

An entry for Docker's `--publish=`.

### mypaas.scale

An integer specifying how many containers should be running for this service.
Can be set to 0 to indicate "non-scaling", which is the default.

When deploying a non-scaling service, the old container is stopped
before starting the new one, resulting in a downtime of a few seconds
This way, there is no risk of multiple containers writing to
the same data at the same time.

If `scaling` is given and larger than zero (so also when 1), a
deployment will have no downtime, because the new containers will be
started and given time to start up before the old containers are
stopped. Note that in this case MyPaas assumes that 1) the container is ready
within 5s, and 2) the container responds 2xx/3xx for the root path "/".

### mypaas.maxcpu

Specify how much of the available CPU resources each container of this
service can use. For instance, if the host machine has two CPUs and you
set `maxcpu` to 1.5, the container is guaranteed at most one and a half
of the CPUs. (This translates to the `--cpu` argument of `docker run`).

### mypaas.maxmem

The maximum amount of memory each container of this service can use.
If you set this option, the minimum allowed (This translates to the
`--memory` argument of `docker run`).
