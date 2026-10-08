#!/usr/bin/env bash
#
# backup_db.sh — Backup semanal de PostgreSQL (GIDAS UCT) + envio por email.
#
# Genera un dump custom (pg_dump -Fc) del volumen postgres_data mediante el
# contenedor `db` del stack, lo comprime, aplica retencion (semanas) y lo envia
# por SMTP a Outlook 365 utilizando send_mail.py.
#
# Uso:
#   ./backup_db.sh                 # ejecuta backup + envio
#   ./backup_db.sh --no-mail       # solo genera el dump, sin enviar
#
# Variables (desde environment / .env.backup):
#   BACKUP_DIR        (default: /home/infra/gidas-backups)
#   RETENTION_WEEKS   (default: 4)  -> conserva las ultimas N semanas
#   SMTP_SENDER, SMTP_TO, SMTP_APP_PASSWORD  (via send_mail.py / .env.backup)
#
# Exit codes:
#   0  exito
#   1  fallo del dump
#   2  fallo del envio (si se solicito)

set -euo pipefail

COMPOSE_DIR="/home/infra/gidas"
BACKUP_DIR="${BACKUP_DIR:-/home/infra/gidas-backups}"
RETENTION_WEEKS="${RETENTION_WEEKS:-4}"
DATE_TAG="$(date +%Y%m%d-%H%M%S)"
DUMP_FILE="${BACKUP_DIR}/gidas-weekly-${DATE_TAG}.dump"
SEND_MAIL="/home/infra/scripts/send_mail.py"
SEND="${1:-mail}"

mkdir -p "${BACKUP_DIR}"

log() { echo "[backup_db][$(date '+%F %T')] $*"; }

# ---- 1. Generar el dump custom desde el contenedor db ---------------------
log "Generando dump: ${DUMP_FILE}"
cd "${COMPOSE_DIR}"

if ! docker compose --env-file .env.production exec -T db \
        pg_dump -U gidas_admin -d gidas_db -Fc --no-owner --no-privileges \
        > "${DUMP_FILE}" 2> "${DUMP_FILE}.log"; then
    log "ERROR: fallo el pg_dump"
    cat "${DUMP_FILE}.log" >&2 || true
    exit 1
fi
rm -f "${DUMP_FILE}.log"

if [ ! -s "${DUMP_FILE}" ]; then
    log "ERROR: el dump generado esta vacio"
    exit 1
fi
SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
log "Dump ok (${SIZE}): ${DUMP_FILE}"

# ---- 2. Aplicar retencion (conservar ultimas RETENTION_WEEKS semanas) -----
# Mantiene los dumps semanales mas recientes y elimina los mas antiguos.
if command -v find >/dev/null 2>&1; then
    find "${BACKUP_DIR}" -maxdepth 1 -name 'gidas-weekly-*.dump' \
        -type f -printf '%T@ %p\n' 2>/dev/null | \
        sort -rn | \
        tail -n +$((RETENTION_WEEKS + 1)) | \
        cut -d' ' -f2- | \
        while IFS= read -r old; do
            log "Purgando dump antiguo: ${old}"
            rm -f "${old}"
        done || true
fi

# ---- 3. Enviar por mail (adjunto) -----------------------------------------
if [ "${SEND}" = "--no-mail" ]; then
    log "Modo no-mail: no se envia. Backup listo en disco."
    exit 0
fi

if [ ! -x "${SEND_MAIL}" ]; then
    # send_mail.py puede no ser ejecutable; lo intentamos con python3
    if command -v python3 >/dev/null 2>&1; then
        log "Enviando por SMTP (python3 ${SEND_MAIL})..."
        if python3 "${SEND_MAIL}" "${DUMP_FILE}"; then
            log "Email enviado ok."
            exit 0
        else
            log "ERROR: fallo el envio del email"
            exit 2
        fi
    else
        log "ERROR: python3 no disponible y send_mail no es ejecutable"
        exit 2
    fi
fi

log "Enviando por SMTP (${SEND_MAIL})..."
if "${SEND_MAIL}" "${DUMP_FILE}"; then
    log "Email enviado ok."
    exit 0
else
    log "ERROR: fallo el envio del email"
    exit 2
fi
