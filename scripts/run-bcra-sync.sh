#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
exec docker compose --env-file "${BCRA_COMPOSE_ENV_FILE:-.env.production}" exec -T backend \
    python -m modules.recursos.jobs.sincronizar_tipos_cambio
