"""
Script that runs the MyPaas daemon (python -m mypaas.server.daemon)
"""

import os
import io
import json
import time
import queue
import datetime
import asyncio
import zipfile

import asgineer

from mypaas.utils import dockercall
from mypaas.server import get_deploy_generator, get_public_key

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
    token = request.querydict.get("token", "")
    signature = request.querydict.get("signature", "")
    if not token or not signature:
        return None

    token_parts = token.split("-")

    # Check the timestamp (first part of the token)
    client_time = int(token_parts[0])
    server_time = int(time.time())
    if not (server_time - 5 <= client_time <= server_time):
        return None  # too late (or early)

    # Validate the signature
    key_fingerprint = token_parts[1]
    public_key = get_public_key(key_fingerprint)
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


@asgineer.to_asgi
async def main(request):
    """ Main entry point
    """
    path = request.path.strip("/")

    if not path:
        return 200, {}, f"Hi there, this is the MyPaas daemon!!"
    elif path == "time":
        return 200, {}, str(int(time.time()))
    elif path == "push":
        return await push(request)
    elif path == "status":
        return await status(request)
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
    blob = await request.get_body(100 * 2 ** 20)  # 100 MiB limit

    # Return generator -> do a deploy while streaming feedback on status
    gen = push_generator(fingerprint, blob)
    return 200, {"content-type": "text/plain"}, gen


async def push_generator(fingerprint, blob):
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

        print(f"Deploy invoked by {fingerprint}")  # log
        yield f"Signature validated with public key (fingerprint {fingerprint}).\n"
        yield f"Let's deploy this!\n"

        # Extract zipfile
        yield "Extracting ...\n"
        deploy_dir = os.path.expanduser("~/_mypaas/deploy_cache")
        os.makedirs(deploy_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(blob), "r") as zf:
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


async def status(request):
    """ Push handler. Authenticate, then return server info.
    """
    if request.method != "GET":
        return 405, {}, "Invalid request"

    fingerprint = authenticate(request)
    if not fingerprint:
        return 403, {}, "Access denied"

    # Return generator
    return 200, {"content-type": "text/plain"}, status_generator(fingerprint)


async def status_generator(fingerprint):

    print(f"Status asked by {fingerprint}")  # log
    yield f"Signature validated with public key (fingerprint {fingerprint}).\n"
    yield f"Collecting status ...\n"

    # First get docker stats
    dstats = dockercall("stats", "--no-stream")
    # Iterate over the lines
    for line in dstats.splitlines()[1:]:
        id_, name, cpu, mem, *rest = line.split()
        info = json.loads(dockercall("inspect", id_))[0]
        status = info["State"]["Status"]
        restarts = info["RestartCount"]
        labels = info["Config"]["Labels"]
        uptime = get_uptime_from_start_time(info["State"]["StartedAt"])
        # Write lines
        yield "\n"
        yield f"Container {name}\n"
        yield f"    Current status: {status}, up {uptime}, {restarts} restarts\n"
        yield f"    Resource usage: {cpu}, {mem}\n"
        yield f"    Has {len(info['Mounts'])} mounts:\n"
        for mount in info["Mounts"]:
            if "Source" in mount and "Destination" in mount:
                yield f"        - {mount['Source']} : {mount['Destination']}\n"
        yield f"    Has {len(labels)} labels:\n"
        for label, val in labels.items():
            yield f"        - {label} = {val}\n"


if __name__ == "__main__":
    # Host on localhost. Traefik will accept https connections and route via
    # localhost:88. Don't allow direct acces, or we have insecure connection.
    asgineer.run(main, "uvicorn", "localhost:88", log_level="warning")
