#!/bin/sh
set -eu

ENV_FILE="${1:-.env.production}"

require_file() {
    if [ ! -f "$1" ]; then
        echo "ERROR: falta el archivo requerido $1" >&2
        exit 1
    fi
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: falta el comando requerido $1" >&2
        exit 1
    fi
}

require_command docker
require_command python3
require_file "$ENV_FILE"

BACKEND_ENV_NAME="$(sed -n 's/^BACKEND_ENV_FILE=//p' "$ENV_FILE" | tail -n 1)"
BACKEND_ENV_NAME="${BACKEND_ENV_NAME:-.env.production}"
BACKEND_ENV_FILE_PATH="backend/$BACKEND_ENV_NAME"
require_file "$BACKEND_ENV_FILE_PATH"

docker compose version >/dev/null
docker compose --env-file "$ENV_FILE" config --quiet
python3 backend/tools/validate_production_topology.py --env-file "$ENV_FILE"
python3 backend/tools/scan_tracked_secrets.py

docker run --rm \
    -v "$PWD/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
    nginxinc/nginx-unprivileged:1.31-alpine3.24 nginx -t

echo "Preflight correcto: Compose, topologia, secretos y Nginx interno validados."
echo "La plantilla Nginx TLS externa es opcional para Cloudflare Tunnel directo a localhost:8080."
echo "Si el laboratorio instala esa alternativa, completar los valores y validar en el host con sudo nginx -t."
