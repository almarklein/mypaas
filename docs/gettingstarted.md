# Getting started with MyPaas


## Get yourself a server

You need a machine to run your PaaS on. You should probably just rent a VM at
a cloud provider. There are many good cloud providers but I can really recommend
[Upcloud](https://upcloud.com/signup/?promo=B8EWX6).
(I personally avoid AWS for ethical reasons.)

So how beefy should the VM be? That depends on what you will run on it,
but a single CPU and 1 GB comes a long way.
I'm running about 15 services on a single VM with 4 GB and 2 CPU's. It's idle most
of the time, and can handle spikes in traffic just fine.


## Initialize the server

Login to your server via SSH. First, you'll need to install some
dependencies. We'll be assuming a fresh Ubuntu VM - you may need to
adjust the commands if you are using another operating system. You may
also need to add `sudo` in front of the commands.

First, let's make sure the package manager is up to date:
```
PaaS-server$ apt update
```

Next, install Docker, start the service, and make sure it starts automatically after a reboot:
```
PaaS-server$ apt install docker.io
PaaS-server$ systemctl start docker
PaaS-server$ systemctl enable docker
```

Now install MyPaas. It is written in Python, so we use pip to install it (you'll need Python 3.6 or higher).
```
PaaS-server$ apt install python3-pip
PaaS-server$ pip3 install mypaas[server]
```
Or to install the current master:
```
PaaS-server$ pip3 install -U git+https://github.com/almarklein/mypaas.git@master#egg=mypaas[server]
```

That's it, you can now initialize your server:
```
PaaS-server$ mypaas server init
```

This will ask you a few questions, and store the answers in a config file.
Further it will make preparations for running your PaaS. You can re-run
this step if you want to reset the PaaS to "factory defaults".
Now there's just one thing left to do:

```
PaaS-server$ mypaas server restart all
```

This will (re)start the router, stats server, and deploy daemon.
Your server is now a PaaS, ready to run apps and services!


## Setting up credentials

Before you can connect your client to your PaaS, you need to setup an
RSA keypair. You can create a new RSA keypair or use an existing SSH
key. See the [security docs](security.md) for details.

To setup your private key, run the following command on your work machine:
```
$ mypaas key-init
```

The server needs your public key to be able to authenticate you.
Copy the public key to your clipboard:
```
$ mypaas key-get
```

Then go back to your server and add the public key to the
`~/_mypaas/authorized_keys` file. You can add multiple public keys to
your server to allow access for multiple devices / developers.

When this is done, you're ready to deploy a service!


## Making your first deploy

Go into a deployable directory and run:
```
$ mypaas push mypaas.yourdomain.com .
```

See the [docs on deploying](deploying.md) for more info.
