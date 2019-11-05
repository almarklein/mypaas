#!/usr/bin/sh

echo 'Stopping and removing current Traefik container (ignore errors)'
docker stop traefik
docker rm traefik

echo 'Launching new Traefik container'
docker run -d --restart always \
  -p 80:80 -p 443:443 -p 8081:8081 --network web \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/_traefik/traefik.toml:/traefik.toml \
  -v ~/_traefik/acme.json:/acme.json \
  -v ~/_traefik/staticroutes.toml:/staticroutes.toml \
  --name traefik traefik:2.0.4

