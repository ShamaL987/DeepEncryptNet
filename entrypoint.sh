#!/bin/bash
set -euo pipefail

# Find Postgres bin dir (version-agnostic)
PG_BIN="$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -n1)"

if [ -z "${PG_BIN}" ] || [ ! -x "${PG_BIN}/initdb" ]; then
  echo "ERROR: PostgreSQL binaries not found. Expected initdb under /usr/lib/postgresql/*/bin"
  ls -la /usr/lib/postgresql || true
  exit 1
fi

INITDB="${PG_BIN}/initdb"
PG_CTL="${PG_BIN}/pg_ctl"
PSQL="${PG_BIN}/psql"
CREATEDB="${PG_BIN}/createdb"

mkdir -p "$PGDATA"
chown -R postgres:postgres /var/lib/postgresql
mkdir -p /var/run/postgresql
chown -R postgres:postgres /var/run/postgresql

# Init cluster if first run
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Initializing PostgreSQL data directory..."
  su - postgres -c "$INITDB -D '$PGDATA'"

  # MVP auth: trust local connections
  echo "host all all 127.0.0.1/32 trust" >> "$PGDATA/pg_hba.conf"
  echo "local all all trust" >> "$PGDATA/pg_hba.conf"
fi

# Start postgres temporarily to create DB if missing
echo "Starting PostgreSQL temporarily..."
su - postgres -c "$PG_CTL -D '$PGDATA' -o \"-c listen_addresses='127.0.0.1'\" -w start"

echo "Ensuring database '${POSTGRES_DB}' exists..."
su - postgres -c "$PSQL -tAc \"SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'\" | grep -q 1 || $CREATEDB '${POSTGRES_DB}'"

echo "Stopping temporary PostgreSQL..."
su - postgres -c "$PG_CTL -D '$PGDATA' -m fast stop"

echo "Starting Supervisor (Postgres + FastAPI)..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/deepencryptnet.conf
