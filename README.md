# MyPaas

MyPaas is a tool that makes it easy to run a platform as a service (PaaS)
on your own VM or hardware. It combines Traefik and Docker, offers free
automatic https, secure deployments via dockerfiles, and analytics.

You can setup your PaaS and make your first deployment in about 5 minutes.


## Docker plus Traefik is awesome

[Docker](https://en.wikipedia.org/wiki/Docker_(software)) makes it
possible to run multiple applications on a single server in a contained
way.

[Traefik](https://traefik.io/) is a modern router, reverse proxy, and
load balancer that can be automatically configured using labels on
Docker containers. It can also act as an https endpoint and
automatically refreshes SSL/TLS certificates with [Let's Encrypt](https://letsencrypt.org/).

[MyPaas](https://github.com/almarklein/mypaas) is a tool that helps you
setup Traefik, and deploy Docker containers that have the right labels
so that Traefik handles them in the right way. Plus it adds
powerful analytics for all your apps. Website traffic is logged
server-side, without coockies, respecting the end user's privacy.


## How it works

MyPaas is a command line interface (CLI) to setup and manage your PaaS server.
You use the same CLI on your work machine to push deploys to the server.
You configure your service/app by writing a Dockerfile and adding special
mypaas-comments to it, and push that to the server via the CLI.
There is a web dashboard, but only for viewing status and analytics.


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


## What about serverless?

Serverless is nice and often very affordable, but you give up control
and you often need additional services for analytics, databases, etc.
MyPaas tries to make managing your server as easy as possible. You
remain in control, and your only costs are that of the VM that the PaaS
runs on.


## Alternatives

Tools similar to MyPaas include [Dokku](http://dokku.viewdocs.io/dokku) and
[CapRover](https://caprover.com). MyPaas' biggest differences are the use of
Traefik (which allows MyPaas itself to be quite small), the way that
deployments work, and the analytics.
