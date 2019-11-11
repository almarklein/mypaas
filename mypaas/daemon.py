"""
Script that runs the MyPaas daemon (python -m mypaas.daemon)
"""

import os
import io
import json
import time
import datetime
import asyncio
import zipfile

import asgineer

from mypaas._utils import dockercall, SERVER_CONFIG_DIR
from mypaas._credentials import load_credentials_at_server, hash_key
from mypaas._deploy import get_deploy_generator

# todo: from ._utils import dockercall


# Fix encoding
os.environ.setdefault("LC_ALL", "C.UTF-8")


global_state = {
    "deploy_in_progress": False,
    "credential_valid_time": 0,
    "current_credentials": {},
}


@asgineer.to_asgi
async def main(request):
    """ Main entry point
    """
    path = request.path.strip("/")

    if not path:
        return 200, {}, f"Hi there!"
    elif path == "push":
        return await push(request)
    elif path == "status":
        return await status(request)
    else:
        return 404, {}, "404 not found"


async def status(request):

    if request.method != "GET":
        return 405, {}, "Invalid request"

    user = authenticate(request)
    if not user:
        return 403, {}, "Access denied"

    out = []

    # First get docker stats
    dstats = dockercall("stats", "--no-stream")
    # Iterate over the lines
    for line in dstats.splitlines()[1:]:
        id_, name, cpu, mem, *rest = line.split()
        info = json.loads(dockercall("inspect", id_))[0]
        status = info["State"]["Status"]
        restart_count = info["RestartCount"]
        labels = info["Config"]["Labels"]
        uptime = get_uptime_from_start_time(info["State"]["StartedAt"])
        # Write lines
        out.append("")
        out.append(f"Container {name}")
        out.append(f"    Current status: {status}, up {uptime}, {restart_count} restarts")
        out.append(f"    Resource usage: {cpu}, {mem}")
        out.append(f"    Has {len(info['Mounts'])} mounts:")
        for mount in info["Mounts"]:
            if "Source" in mount and "Destination" in mount:
                out.append(f"        - {mount['Source']} : {mount['Destination']}")
        out.append(f"    Has {len(labels)} labels:")
        for label, val in labels.items():
            out.append(f"        - {label} = {val}")

    return 200, {}, "\n".join(out)


async def push(request):
    """ Push handler. Check credentials, then return generator.
    """
    if request.method != "POST":
        return 405, {}, "Invalid request"

    user = authenticate(request)
    if not user:
        return 403, {}, "Access denied"

    # Get given file
    blob = await request.get_body(100 * 2 ** 20)  # 100 MiB limit

    # Return generator -> do a deploy while streaming feedback on status
    gen = push_generator(request, user, blob)
    return 200, {"content-type": "text/plain"}, gen


async def push_generator(request, user, blob):
    """ Generator that extracts given zipfile and does the deploy.
    """

    # Make sure that only one push happens at a given time
    if global_state["deploy_in_progress"]:
        yield "Another deploy is in progress. Please wait.\n"
        while global_state["deploy_in_progress"]:
            await asyncio.sleep(0.1)
    global_state["deploy_in_progress"] = True
    # Really, really make sure we set this back to False when done!

    try:

        yield f"Hi {user}, this is the MyPaas daemon. Let's deploy this!\n"
        print(f"Deploy invoked by {user}")  # log

        # Extract zipfile
        yield "Extracting ...\n"
        deploy_dir = SERVER_CONFIG_DIR + "/deploy_cache"
        os.makedirs(deploy_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(blob), "r") as zf:
            zf.extractall(deploy_dir)

        # Deploy
        for step in get_deploy_generator(deploy_dir):
            yield step + "\n"

    except Exception as err:
        yield "FAIL: " + str(err)
    finally:
        global_state["deploy_in_progress"] = False


def get_uptime_from_start_time(start_time):
    start_time = start_time.rpartition(".")[0] + "+0000"  # get rid of subsecs
    started = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S%z")
    now = datetime.datetime.now(datetime.timezone.utc)
    nsecs = ori_nsecs = (now - started).seconds
    result = []
    if ori_nsecs >= 86400:
        result.append(f"{nsecs / 86400:0.0f} days")
        nsecs = nsecs % 86400
    if ori_nsecs >= 3600:
        result.append(f"{nsecs / 3600:0.0f} hours")
        nsecs = nsecs % 3600
    if ori_nsecs >= 60:
        result.append(f"{nsecs / 3600:0.0f} min")
        nsecs = nsecs % 60
    result.append(f"{nsecs:0.0f} secs")
    return " ".join(result[:2])


def authenticate(request):
    # Get given credentials
    key1 = request.querydict.get("key1", "")
    key2 = request.querydict.get("key2", "")
    if not key1 or not key2:
        return None

    # Get registered user credentials
    if time.time() > global_state["credential_valid_time"]:
        global_state["credential_valid_time"] = time.time() + 10
        global_state["current_credentials"] = load_credentials_at_server()
    our_credentials = global_state["current_credentials"]

    # Check credentials
    valid_user = None
    incoming_key_hashes = hash_key(key1), hash_key(key2)
    for user, key_hashes in our_credentials.items():
        if tuple(key_hashes) == incoming_key_hashes:
            valid_user = user

    return valid_user


if __name__ == "__main__":
    # Host on localhost. Traefik will accept https connections and route via
    # localhost:88. Don't allow direct acces, or we have insecure connection.
    asgineer.run(main, "uvicorn", "localhost:88", log_level="warning")
