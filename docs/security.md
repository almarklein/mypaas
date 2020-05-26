# MyPaas security

MyPaas is probably more secure than most other self-hosted (or hosted) PaaS
solutions.


## Passwords, 2FA, and RSA

Many online services offfer a web UI to control your system. You typically
login to this system using a username and password. But passwords are
vulnerable in different ways:

* People tend to re-use passwords, so if one service becomes compromised
  attackers might have access to other services as well.
* Passwords can be guessed, or detected by looking over your shoulder.
* Passwords can be sniffed via a man-in-the-middle attack (because the
  password is send over).

Much of this can be improved by using 2-factor authentication. We strongly
recommend using it e.g. for logging in to the service where you rent your VM.
The reason why 2FA is better is that it adds an "ownership factor" (read
[this excelent post](https://did.app/articles/the-three-factors-of-authentication)
on the three factors of authentication).

But we go one step further, using a technique also used by SSH: RSA
keypairs. These consists of a private key (a secret) and a public key.
This makes it possible for the owner of the private key to make a claim
(e.g. sign a piece of data). And anyone who owns the public key can
verify that claim.

RSA keypairs are also an "ownership factor". Plus they can be
encrypted with a user password, which acts as an extra
layer of security in case your private key is compromised.


## Security of deployments

Deployments are secured with an RSA keypair. The easiest is to use an existing
key; you probably already have one for SSH access, or because you work with Git.

When the client pushes a deployment, the payload (the zipped bundle of files)
are signed with the private key. Further a small token is send that is also
signed.

This token contains a timestamp, rendering it invalid after a certain amount
of time (so an attacker cannot re-use it).

The server receives this deployment requests. It will first check the token
and verify that it has indeed been signed by your private key. The server
has the public key to do this. When this succeeds, it can be certain that you
own the private key. The server will then continue to download the payload,
and verify it using a second signature. This makes sure that the payload
has not been tempered with.

On top of this, all communication runs exclusively over https. There are thus
multiple layers of security.


## Deployments from CI/CD

When you want to deploy from CI/CD, you must set the environment
variable `MYPAAS_PRIVATE_KEY`. You can generate a key for this using
`mypaas key_gen`.


## Security for viewing status and analytics

The security for the status and analytics pages is not critically important,
because one can only view data, not make any changes. Nevertheless, this
information may be useful to an attacker, because it may give the attacker
insight into whether his/her actions have the desired effect. Therefore,
these pages are protected with a username and password.
