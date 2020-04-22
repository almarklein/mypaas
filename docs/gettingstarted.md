# Getting started with MyPaas


## Initialize the server

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
