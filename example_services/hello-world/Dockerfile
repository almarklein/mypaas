# Example Dockerfile for a simple web server.
#
# This specifies the name of the service:
# mypaas.service = hello-world
#
# This specifies what domain and path to host on, and whether to enable SSL.
# This option can be specied multiple times:
# mypaas.url = https://mypaas.canpute.com/hello
#
# This specifies how many instances there will be. The default is 0,
# which means one container is running at any time (also during a deploy):
# mypaas.scale = 1
#
# It is recommended to limit the container. In case it has a memory leak,
# you'd rather have the container restarted than it crashing the server:
# mypaas.maxcpu = 1.0
# mypaas.maxmem = 500m
#
# Environment variables can be specified too. By not giving it a value,
# the value is sampled from the env section in ~/_mypaas/config.toml,
# you can use it to specify secrets like API tokens.
# mypaas.env = FOO=bar
# mypaas.env = EXAMPLE_SECRET


FROM python:3.8-slim-buster

RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1

WORKDIR /root
COPY . .
CMD ["python", "server.py"]
