#!/usr/bin/env python3
"""
send_mail.py — Envia un backup de PostgreSQL de GIDAS por SMTP adjunto.

Canal: Outlook 365 (smtp.office365.com:587, STARTTLS).
Cuenta remitente: infrait@frlp.utn.edu.ar (app-password).
Destinatarios: gidas@frlp.utn.edu.ar e infra@frlp.utn.edu.ar (configurables).

Uso:
    send_mail.py <archivo_adjunto> [--subject "texto"] [--body "texto"]

Configuracion (desde /home/infra/gidas/.env.backup):
    SMTP_HOST=smtp.office365.com
    SMTP_PORT=587
    SMTP_SENDER=infrait@frlp.utn.edu.ar
    SMTP_APP_PASSWORD=********   (app-password / contrasena de la cuenta)
    SMTP_TO=gidas@frlp.utn.edu.ar,infra@frlp.utn.edu.ar

Exit codes: 0 ok, 1 error.

NOTA: el archivo .env.backup tiene permisos 600 y NO se documenta ni versiona.
"""

import os
import sys
import smtplib
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate
from pathlib import Path

ENV_FILE = Path("/home/infra/gidas/.env.backup")


def load_env(path: Path) -> dict:
    """Carga pares CLAVE=VALOR de un archivo de entorno (ignora # y vacios)."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Envia backup por SMTP adjunto")
    parser.add_argument("attachment", help="Ruta del archivo dump a adjuntar")
    parser.add_argument("--subject", default="Backup semanal BBDD GIDAS")
    parser.add_argument("--body", default="")
    args = parser.parse_args()

    env = load_env(ENV_FILE)

    host = env.get("SMTP_HOST", "smtp.office365.com")
    port = int(env.get("SMTP_PORT", "587"))
    sender = env.get("SMTP_SENDER", "infrait@frlp.utn.edu.ar")
    password = env.get("SMTP_APP_PASSWORD")
    to_list = [t.strip() for t in env.get("SMTP_TO", "").split(",") if t.strip()]

    if not password:
        print("ERROR: SMTP_APP_PASSWORD no definido en %s" % ENV_FILE, file=sys.stderr)
        return 1
    if not to_list:
        print("ERROR: SMTP_TO vacio en %s" % ENV_FILE, file=sys.stderr)
        return 1

    attachment = Path(args.attachment)
    if not attachment.exists():
        print("ERROR: adjunto no existe: %s" % attachment, file=sys.stderr)
        return 1

    size = attachment.stat().st_size / (1024 * 1024)  # MB
    body = args.body or (
        "Backup semanal de la base de datos GIDAS UCT.\n\n"
        "Adjunto: %s (%.2f MB)\n"
        "Generado: %s\n"
        "Para recuperar: docker compose --env-file .env.production exec -T db "
        "pg_restore -U gidas_admin -d gidas_db --clean %s\n"
        % (attachment.name, size, attachment.stat().st_mtime, attachment.name)
    )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with attachment.open("rb") as f:
        part = MIMEApplication(f.read(), _subtype="octet-stream")
    part.add_header("Content-Disposition", "attachment",
                    filename=attachment.name)
    msg.attach(part)

    try:
        with smtplib.SMTP(host, port, timeout=60) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(sender, password)
            smtp.sendmail(sender, to_list, msg.as_string())
        print("Email enviado a: %s" % ", ".join(to_list))
        return 0
    except Exception as exc:  # noqa: BLE001 - reportar y fallar
        print("ERROR al enviar email: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
