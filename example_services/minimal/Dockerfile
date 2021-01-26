# mypaas.service = minimal
#
# mypaas.url = https://example.com/minimal
#
# mypaas.scale = 3
# mypaas.healthcheck = /status 11s 2s
# mypaas.maxmem = 500m


FROM python:3.8-slim-buster

RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer

WORKDIR /root
COPY . .
CMD ["python", "server.py"]
