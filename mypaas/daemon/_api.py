"""
Http API for the mypaas daemon.
"""

import os
import io
import time
import queue
import shutil
import logging
import datetime
import asyncio
import zipfile

from mypaas.server import get_deploy_generator, get_public_key


logger = logging.getLogger("mypaasd")

# Fix encoding
os.environ.setdefault("LC_ALL", "C.UTF-8")

# Keep track of tokens that have been used. These expire after x seconds.
invalid_tokens = queue.deque()  # contains (timestamp, token) tuples

# Keep track of whether a deploy is in progress.
deploy_in_progress = False


# %% Utilities


def authenticate(request):
    """ Check if the request comes from someone that has a private key
    that we have have authorized.

    This is done by validating (using the public key) that the token is
    signed correctly. We also make sure that keys can only be used once.
    """

    # Get authentication details
    key_id = request.querydict.get("id", "")  # aka fingerprint
    token = request.querydict.get("token", "")
    signature = request.querydict.get("sig1", "")
    if not token or not signature:
        return None

    # Check the timestamp (first part of the token)
    client_time = int(token.split("-")[0])
    server_time = int(time.time())
    if not (server_time - 5 <= client_time <= server_time):
        return None  # too late (or early)

    # Validate the signature
    public_key = get_public_key(key_id)
    if public_key is None:
        return None
    if not public_key.verify_data(signature, token.encode()):
        return None

    # Ok, but what if someone somehow read the key during its transfer
    # and tries to re-use it?
    for _, invalid_token in invalid_tokens:
        if token == invalid_token:
            return None

    # Clear invalid tokens that have expired and mark this one as invalid
    old = server_time - 10
    while invalid_tokens and invalid_tokens[0][0] < old:
        invalid_tokens.popleft()
    invalid_tokens.append((server_time, token))

    # todo: return string based on "comment" in public key.
    return public_key.get_id()  # fingerprint


def validate_payload(request, payload):
    """ Verify that the given payload matches the signature.
    """
    # Get authentication details
    key_id = request.querydict.get("id", "")  # aka fingerprint
    signature = request.querydict.get("sig2", "")
    if not signature:
        return None

    # Validate the payload
    public_key = get_public_key(key_id)
    if public_key is None:
        return None
    if not public_key.verify_data(signature, payload):
        return None

    return public_key.get_id()


def get_uptime_from_start_time(start_time):
    start_time = start_time.rpartition(".")[0] + "+0000"  # get rid of subsecs
    started = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S%z")
    now = datetime.datetime.now(datetime.timezone.utc)
    nsecs = ori_nsecs = (now - started).seconds
    result = []
    if ori_nsecs >= 86400:
        result.append(f"{int(nsecs / 86400)} days")
        nsecs = nsecs % 86400
    if ori_nsecs >= 3600:
        result.append(f"{int(nsecs / 3600)} hours")
        nsecs = nsecs % 3600
    if ori_nsecs >= 60:
        result.append(f"{int(nsecs / 60)} min")
        nsecs = nsecs % 60
    result.append(f"{int(nsecs)} secs")
    return " ".join(result[:2])


# %% Handlers

MAIN_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MyPaas Daemon</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/style.css">
</head>
<body>

<h1>MyPaas Daemon</h1>

<p style='max-width: 700px;'>
Hi! This is the MyPaas daemon that handles the deploys. It also measures
the system's CPU, memory and disk usage, as well as the CPU and memory
usage of the other MyPaas services, and sends these measurements to the
stats server.
</p>

</body>
</html>
""".lstrip()


async def main_handler(request):
    """ Main entry point
    """
    if request.path.startswith("/daemon/"):
        path = request.path[7:]
    else:
        return 404, {}, "404 not found"

    if path == "/":
        return 200, {}, MAIN_HTML
    elif path == "/time":
        return 200, {}, str(int(time.time()))
    elif path == "/push":
        return await push(request)
    else:
        return 404, {}, "404 not found"


async def push(request):
    """ Push handler. Authenticate, then return generator.
    """
    if request.method != "POST":
        return 405, {}, "Invalid request"

    fingerprint = authenticate(request)
    if not fingerprint:
        return 403, {}, "Access denied"

    # Get given file
    payload = await request.get_body(100 * 2 ** 20)  # 100 MiB limit

    # Also validate it
    if not validate_payload(request, payload):
        return 403, {}, "Payload could not be verified."

    # Return generator -> do a deploy while streaming feedback on status
    gen = push_generator(fingerprint, payload)
    return 200, {"content-type": "text/plain"}, gen


async def push_generator(fingerprint, payload):
    """ Generator that extracts given zipfile and does the deploy.
    """
    global deploy_in_progress

    # Make sure that only one push happens at a given time
    if deploy_in_progress:
        yield f"Another deploy is in progress by {deploy_in_progress}. Please wait.\n"
        while deploy_in_progress:
            await asyncio.sleep(1)
            yield "."
    deploy_in_progress = True  # Really, really make sure we set this back to False!

    try:

        logger.warn(f"Deploy invoked by {fingerprint}")  # log
        yield f"Hi! This is the MyPaas server. Let's deploy this!\n"
        yield f"Signature validated with public key (fingerprint {fingerprint}).\n"

        # Extract zipfile
        yield "Extracting ...\n"
        deploy_dir = os.path.expanduser("~/_mypaas/deploy_cache")
        shutil.rmtree(deploy_dir, ignore_errors=True)
        os.makedirs(deploy_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
            zf.extractall(deploy_dir)

        # Deploy
        await asyncio.sleep(0.1)
        for step in get_deploy_generator(deploy_dir):
            await asyncio.sleep(0.1)
            yield step + "\n"

    except Exception as err:
        yield "FAIL: " + str(err)
    finally:
        deploy_in_progress = False
