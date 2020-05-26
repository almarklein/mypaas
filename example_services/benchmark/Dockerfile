# mypaas.service = dbtest
# mypaas.url = https://mypaas2.canpute.com/dbtest
# mypaas.scale = 3
# mypaas.volume = /root/_dbtest:/root/_dbtest

FROM python:3.8-slim-buster

RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1

WORKDIR /root
COPY . .
CMD ["python", "server.py"]
