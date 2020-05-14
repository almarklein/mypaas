"""
The CLI for mypaas.
"""

import sys

import mypaas
from mypaas import __version__, __traefik_version__


def server_help():
    """ Show this help message and exit.
    """
    print(server_docs)


def client_help():
    """ Show this help message and exit.
    """
    print(client_docs)


server_help.__name__ = client_help.__name__ = "help"


def version():
    """ Print version.
    """
    print(f"mypaas v{__version__} (using Traefik v{__traefik_version__})")


def _make_func_dict_and_docs(*args):
    funcs = {}
    description = "usage: mypaas command [arguments]"
    description += "\n\n" + mypaas.__doc__.strip() + "\n\n"

    for func in args:
        if isinstance(func, str):
            description += func + "\n\n"  # header
        else:
            funcs[func.__name__] = func
            funcs[func.__name__.replace("_", "-")] = func
            co = func.__code__
            arg_names = " ".join(x.upper() for x in co.co_varnames[: co.co_argcount])
            description += "    " + func.__name__ + " " + arg_names + "\n"
            doc = "    " + func.__doc__.strip()
            description += doc.replace("    ", "        ") + "\n"

    return funcs, description


server_funcs, server_docs = _make_func_dict_and_docs(
    "Commands to run at the PaaS server:",
    version,
    server_help,
    mypaas.server.init,
    mypaas.server.restart,
    mypaas.server.deploy,
    mypaas.server.schedule_reboot,
)


client_funcs, client_docs = _make_func_dict_and_docs(
    "This is the client CLI. Use 'mypaas server ..' for server commands.\n"
    + "Commands to run at your work machine:",
    version,
    client_help,
    mypaas.client.key_init,
    mypaas.client.key_gen,
    mypaas.client.key_get,
    mypaas.client.push,
)


def main(argv=None):

    assert sys.version_info.major == 3, "This script needs to run with Python 3."

    # Get CLI args and determine whether we run as server
    if argv is None:
        argv = sys.argv[1:]
    is_server = False
    if argv and argv[0] == "server":
        is_server = True
        argv = argv[1:]
    elif sys.argv[0].endswith(("-server", "_server")):
        is_server = True
    if not argv:
        argv = ["help"]

    # Get function to call
    if is_server:
        if argv[0] in server_funcs:
            func = server_funcs[argv[0]]
        elif argv[0] in client_funcs:
            sys.exit(f"MyPaas subcommand {argv[0]} is a client (not server) command.")
        else:
            sys.exit(f"Invalid use of mypaas: {argv}")
    else:
        if argv[0] in client_funcs:
            func = client_funcs[argv[0]]
        elif argv[0] in server_funcs:
            sys.exit(f"MyPaas subcommand {argv[0]} is a server (not client) command.")
        else:
            sys.exit(f"Invalid use of mypaas: {argv}")

    # Call it
    try:
        func(*argv[1:])
    except RuntimeError as err:
        # Inside the functions, RunTimeError is raised in situations
        # that can sufficiently be described with the error message.
        # Other exceptions fall through, and their traceback is
        # printed.
        sys.exit(str(err))


if __name__ == "__main__":
    main()
