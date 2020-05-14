# Getting started with MyPaas


## Initialize the server

Login to your server via SSH. First, you'll need to install some
dependencies. We'll be assuming a fresh Ubuntu VM - you may need to
adjust the commands if you are using another operating system. You may
also need to add `sudo` in front of the commands.

First, let's make sure the package manager is up to date:
```
PaaS server$ apt update
```

Next, install Docker, start the service, and make sure it starts automatically after a reboot:
```
PaaS server$ apt install docker.io
PaaS server$ systemctl start docker
PaaS server$ systemctl enable docker
```

Now install MyPaas. It is written in Python, so we use pip to install it (you'll need Python 3.6 or higher).
```
PaaS server$ apt install python3-pip
PaaS server$ pip3 install mypaas[server]
```

That's it, you can now initialize your server:
```
PaaS server$ mypaas server init
```

This will ask you a few questions, and store the answers in a config file.
Further it will make preparations for running your PaaS. You can re-run
this step if you want to reset the PaaS to "factory defaults".
Now there's just one thing left to do:

```
PaaS server$ mypaas server restart all
```

This will (re)start the router, stats server, and deploy daemon.
Your server is now a PaaS, ready to run apps and services!


## Setting up credentials

Before you can connect your client to your PaaS, you need to authenticate it.

MyPaas works with RSA key pairs. This means that there is a private key on
your device, which must be kept secret. This key is also encrypted with a
password for an extra layer of security. The corresponding public key is
added to a list at the server. The server uses the public key to confirm that
the client is who it claims to be. This key is public, you can safely email it
to somewhere (or post it on-line, if you want).

To setup your keypair, run the following command on your work machine:
```
$ mypaas key-init
```

If you choose to use the same RSA key as for SSH, you are now done. Otherwise,
you need to let the server know your public key. Copy the public key to your clipboard:
```
$ mypaas key-get
```

Then go back to your server and add the public key to the
`~/_mypaas/authorized_keys` file. You can add multiple public keys to
your server to allow access for multiple devices / developers.
Note that the keys in `~/.ssh/authorized_keys` also work.

When this is done, you're ready to deploy a service!


## Making your first deploy

Go into a deployable directoru and run:
```
$ mypaas push mypaas.yourdomain.com .
```

See the [docs on deploying](deploying.md) for more info.
