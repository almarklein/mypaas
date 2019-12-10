"""
CLI for mypaas
"""

import sys

import mypaas
from mypaas import __version__, __traefik_version__


def help():
    """ Show this help message and exit.
    """
    print(docs)


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
            description += "\n" + func + "\n\n"  # header
        else:
            funcs[func.__name__] = func
            funcs[func.__name__.replace("_", "-")] = func
            co = func.__code__
            arg_names = " ".join(x.upper() for x in co.co_varnames[: co.co_argcount])
            description += "    " + func.__name__ + " " + arg_names + "\n"
            doc = "    " + func.__doc__.strip()
            description += doc.replace("    ", "        ") + "\n"

    return funcs, description


funcs, docs = _make_func_dict_and_docs(
    help,
    version,
    "Commands to run at the PAAS server:",
    mypaas.server_init,
    mypaas.server_deploy,
    mypaas.server_restart_traefik,
    mypaas.user_add,
    mypaas.user_list,
    mypaas.user_remove,
    "Commands to run at a remote machine (e.g. CI/CD or your laptop):",
    mypaas.key_init,
    mypaas.key_get,
    mypaas.key_create,
    mypaas.push,
    mypaas.status,
)


def main(argv=None):

    assert sys.version_info.major == 3, "This script needs to run with Python 3."

    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["help"]

    if argv[0] in funcs:
        func = funcs[argv[0]]
        try:
            func(*argv[1:])
        except RuntimeError as err:
            # Inside the functions, RunTimeError is raised in situations
            # that can sufficiently be described with the error message.
            # Other exceptions fall through, and their traceback is
            # printed.
            sys.exit(str(err))
    else:
        sys.exit(f"Invalid use of mypaas: {argv}")


if __name__ == "__main__":
    main()
