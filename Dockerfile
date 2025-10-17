# Dockerfile
FROM postgres:16-alpine


# Default database name
ENV POSTGRES_DB=flows

# Optional: store data in a persistent volume
VOLUME ["/var/lib/postgresql/data"]

EXPOSE 5432
