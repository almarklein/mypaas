# Example to run a PostgreSQL database
#
# Deploying this runs the database in a container. All services on the
# same server can connect to it using the service name ("postgres") as
# the hostname. See the hello-world example.
#
# IMPORTANT! In production, remove the "=1234"
# and set the POSTGRES_PASSWORD on the server in ~/_mypaas/config.toml
#
# mypaas.service = postgres
# mypaas.env = POSTGRES_PASSWORD=1234
# mypaas.volume = ~/_postgres:/var/lib/postgresql/data

FROM postgres
