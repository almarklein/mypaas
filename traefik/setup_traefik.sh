docker network create mypaas-net
mkdir ~/_traefik
touch ~/_traefik/acme.json
chmod 600 ~/_traefik/acme.json
cp traefik-template.toml ~/_traefik/traefik.toml

