import random
import subprocess


def input_ask_bool(s):
    while True:
        x = input(s)
        if x.lower() in ("y", "yes"):
            return True
        elif x.lower() in ("n", "no"):
            return False
        else:
            print("Invalid answer. Please answer with one of: 'y', 'yes', 'n', 'no'.\n")


def input_ask_int(s, valid_numbers):
    while True:
        x = input(s)
        try:
            n = int(x)
        except ValueError:
            pass
        else:
            if n in valid_numbers:
                return n
        print("Invalid answer. Please provide a valid number.\n")


def generate_uid(n=8):
    """ Generate a unique id in the form of an 8-char string
    """
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    nchars = len(chars)  # 52, so 52**8 => 53459728531456 possibilities
    return "".join([chars[int(random.random() * nchars)] for i in range(n)])


# def appdata_dir(appname="mypaas"):
#     """ Get the path to the application directory, where applications
#     are allowed to write user specific files (e.g. configurations).
#     """
#
#     # Define default user directory
#     userDir = os.path.expanduser("~")
#     if not os.path.isdir(userDir):  # pragma: no cover
#         userDir = "/var/tmp"
#
#     # Get system app data dir
#     path = None
#     if sys.platform.startswith("win"):
#         path = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
#     elif sys.platform.startswith("darwin"):
#         path = os.path.join(userDir, "Library", "Application Support")
#     # On Linux and as fallback
#     if not (path and os.path.isdir(path)):
#         path = userDir
#
#     # Get path specific for this app
#     if appname:
#         if path == userDir:
#             appname = "." + appname.lstrip(".")  # Make it a hidden directory
#         path = os.path.join(path, appname)
#         if not os.path.isdir(path):  # pragma: no cover
#             os.makedirs(path, exist_ok=True)
#
#     return path


def dockercall(*args, fail_ok=False):
    cmd = ["docker"]
    cmd.extend(args)
    try:
        output_bytes = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return output_bytes.decode(errors="ignore").strip()
    except subprocess.CalledProcessError as err:
        output = err.output.decode(errors="ignore").strip()
        if fail_ok:
            return output
        else:
            header = "=======> Calling [docker, " + str(cmd)[1:] + "\n"
            raise RuntimeError(header + output + "\n=======> Error in Docker call!")
