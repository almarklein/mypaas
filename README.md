# MyPaas

MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, offers free
automatic https, secure deployments via dockerfiles, and analtytics.


## Docker plus Traefik is awesome

[Docker](https://en.wikipedia.org/wiki/Docker_(software)) makes it
possible to run multiple applications on a single server in a contained
way, and setting (memory and CPU) limits on each container.

[Traefik](https://traefik.io/) is a modern router, reverse proxy, and
load balancer that can be automatically configured using labels on
Docker containers. It can also act as an https endpoint and
automatically refreshes SSL/TLS certificates with [Let's Encrypt](https://letsencrypt.org/).

[MyPaas](https://github.com/almarklein/mypaas) is a tool that helps you
setup Traefik, and deploy Docker containers that have the right labels
so that Traefik handles them in the right way. Plus it adds some
basic analytics.


## How it works

MyPaas is a command line utility that you use both on your server (the
PAAS), as well as on other machines to push deploys to your server. You
configure your service by writing a Dockerfile and adding special
comments to it, and push that to the server via the cli.
There is a dashboard, but only for viewing status and analytics.


## Setting expectations

Using MyPaas requires you to be familiar with a few basic backend
development skills. There are plenty of online guides on each topic.

* You must be able to SSH into your server.
* You must know how to edit a file over SSH.
* You should probably know the basics of Docker.
* It may be useful to know the basics commands of systemctl
  (actually, `systemctl status mypaasd` may be all you need).


## Guide

* [Getting started](docs/gettingstarted.md)
* [Deploying](docs/deploying.md)
* [Checking status and analytics](docs/status.md)
* [The CLI](docs/cli.md)
* [Notes on security](docs/security.md)


## License

BSD 2-clause.
