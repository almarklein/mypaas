"""
The MyPaas setup script.
"""

import os

try:
    import setuptools  # noqa, analysis:ignore
except ImportError:
    pass  # setuptools allows for "develop", but it's not essential

from distutils.core import setup


def get_version_and_doc(filename):
    ns = dict(__version__="", __doc__="")
    docstatus = 0  # Not started, in progress, done
    for line in open(filename, "rb").read().decode().splitlines():
        if line.startswith("__version__"):
            exec(line.strip(), ns, ns)
        elif line.startswith('"""'):
            if docstatus == 0:
                docstatus = 1
                line = line.lstrip('"')
            elif docstatus == 1:
                docstatus = 2
        if docstatus == 1:
            ns["__doc__"] += line.rstrip() + "\n"
    if not ns["__version__"]:
        raise RuntimeError("Could not find __version__")
    return ns["__version__"], ns["__doc__"]


# Get version and docstring (i.e. long description)
version, doc = get_version_and_doc(
    os.path.join(os.path.dirname(__file__), "mypaas", "__init__.py")
)


client_requires = ["cryptography", "requests", "pyperclip"]
server_requires = ["toml", "uvicorn", "asgineer", "psutil", "fastuaparser", "pscript"]


setup(
    name="mypaas",
    version=version,
    author="Almar Klein",
    author_email="",
    license="2-clause BSD",
    url="https://github.com/almarklein/mypaas",
    keywords="paas, saas, deployment, traefik, docker",
    description="Run your own PaaS using Docker, Traefik, and great monitoring",
    long_description=doc,
    platforms="any",
    python_requires=">=3.6",
    install_requires=client_requires,
    extras_require={"server": server_requires},
    packages=[
        "mypaas",
        "mypaas.utils",
        "mypaas.client",
        "mypaas.server",
        "mypaas.daemon",
        "mypaas.stats",
    ],
    entry_points={"console_scripts": ["mypaas = mypaas.__main__:main"]},
    zip_safe=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
