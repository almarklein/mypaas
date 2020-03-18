# Example Dockerfile for a simple web server. Replace the url with your own.
#
# mypaas.service=hello-world
# mypaas.url=https://mypaas.canpute.com/hello

FROM python:3.8-slim-buster

# Install Python requirements and dev requirements
RUN apt update \
    && pip --no-cache-dir install pip --upgrade \
    && pip --no-cache-dir install uvicorn uvloop httptools \
    && pip --no-cache-dir install asgineer==0.7.1

WORKDIR /root
COPY . .
CMD python server.py
