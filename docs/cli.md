# MyPaas CLI commands


## On the client (your work machine)

```
$ mypaas
```
```
usage: mypaas command [arguments]

MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.

This is the client CLI. Use 'mypaas server ..' for server commands.
Commands to run at your work machine:

    version
        Print version.
    help
        Show this help message and exit.
    key_init
        Setup a keypair to authorize this machine to a MyPaas server.
        The private key is stored on this machine and should be kept secret.
        You can also choose to use an existing RSA key.
    key_gen
        Generate (but not store) a generic (passwordless) SSH keypair,
        e.g. to use in CI/CD.
    key_get
        Get the public key corresponding to the private key on this machine.
        This public key can be shared. The key is printed and copied to the
        clipboard.
    push DOMAIN DIRECTORY
        Push the given directory to your PAAS, where it will be
        deployed as an app/service. The directory must contain at least a
        Dockerfile.
```


## On the server

```
$ mypaas server
```
```
usage: mypaas command [arguments]

MyPaas is a tool that makes it easy to run a platform as a service (PAAS)
on your own VM or hardware. It combines Traefik and Docker, enabling free
automatic https (via Let's Encrypt) and deployments via dockerfiles.

Commands to run at the PAAS server:

    version
        Print version.
    help
        Show this help message and exit.
    init
        Initialize the current machine to be a PAAS. You will be asked
        a few questions, so Traefik and the deploy server can be configured
        correctly.
    deploy DEPLOY_DIR
        Deploy the current directory as a service. The directory must
        contain at least a Dockerfile. In most cases you should probably
        'mypaas push' from your work machine instead.
    restart_daemon
        Restart the mypaas daemon.
    restart_traefik
        Restart the Traefik docker container. You can run this after
        updating the config (~/_mypaas/traefik.toml or staticroutes.toml)
        or to update Traefik after updating MyPaas. Your PAAS will be
        offline for a few seconds.
    schedule_reboot WHEN
        Create a timer+service to reboot the server at a regular interval,
        e.g. every sunday. The default value for when is "Sun 06:00:00".
```
