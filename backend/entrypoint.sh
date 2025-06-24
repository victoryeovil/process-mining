#!/usr/bin/env bash
set -e

# If DATABASE_URL is SQLite, skip Postgres wait entirely
if [[ "$DATABASE_URL" == sqlite* ]]; then
  echo "⚠️  Detected SQLite ($DATABASE_URL) – skipping Postgres wait"
  echo "✅  Running migrations against SQLite"
  python manage.py migrate --noinput
  exec "$@"
fi

# Otherwise assume Postgres.  Allow overriding with DB_HOST/DB_PORT, else default to 'db:5432'
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
FALLBACK_HOST=localhost

wait_for_pg() {
  local host=$1
  echo "⏳ Waiting for Postgres at ${host}:${DB_PORT}..."
  until PGPASSWORD="$POSTGRES_PASSWORD" \
        psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\l' \
        >/dev/null 2>&1; do
    sleep 2
    echo "⏳ Still waiting for Postgres at ${host}:${DB_PORT}..."
  done
  echo "✅ Connected to Postgres at ${host}:${DB_PORT}"
}

# Try primary host
if ! wait_for_pg "$DB_HOST"; then
  # If it ever exits (it won’t, since wait_for_pg loops), we’d fallback here…
  echo "⚠️  Could not reach ${DB_HOST}, falling back to ${FALLBACK_HOST}"
  wait_for_pg "$FALLBACK_HOST"
fi

echo "✅  Running Django migrations"
python manage.py migrate --noinput

# Finally exec the CMD (e.g. gunicorn …)
exec "$@"
