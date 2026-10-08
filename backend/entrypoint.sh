#!/bin/sh
set -e

echo "Esperando a PostgreSQL..."

# m3 (menor): loop acotado para fallar rapido si la DB no levanta.
wait_timeout="${DB_WAIT_TIMEOUT:-120}"
elapsed=0
while ! python -c "
import os
import psycopg2
from urllib.parse import urlparse

db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise Exception('DATABASE_URL no está definida')

url = urlparse(db_url)

conn = psycopg2.connect(
    dbname=url.path.lstrip('/'),
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
conn.close()
"; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ "$elapsed" -ge "$wait_timeout" ]; then
    echo "Error: PostgreSQL no disponible tras ${wait_timeout}s. Abortando." >&2
    exit 1
  fi
done


while ! python -c "
import os
import psycopg2
from urllib.parse import urlparse

db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise Exception('DATABASE_URL no está definida')

url = urlparse(db_url)

conn = psycopg2.connect(
    dbname=url.path.lstrip('/'),
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
conn.close()
"; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ "$elapsed" -ge "$wait_timeout" ]; then
    echo "Error: PostgreSQL no disponible tras ${wait_timeout}s. Abortando." >&2
    exit 1
  fi
done

echo "PostgreSQL disponible"

if [ "${ENTRYPOINT_MODE:-serve}" = "migrate" ]; then
  echo "Preparando rol de aplicacion..."
  python tools/manage_database_roles.py prepare

  echo "Aplicando migraciones..."
  flask db upgrade

  echo "Ejecutando seed inicial..."
  python seed_roles.py

  echo "Aplicando permisos de minimo privilegio..."
  python tools/manage_database_roles.py grant
  echo "Migraciones y permisos completados"
  exit 0
fi

echo "Iniciando backend..."

if [ "${APP_ENV}" = "production" ] || [ "${APP_ENV}" = "prod" ]; then
  exec gunicorn "app:app" \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
    --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
    --access-logfile - \
    --error-logfile -
fi

exec flask run --host=0.0.0.0 --port=5000
