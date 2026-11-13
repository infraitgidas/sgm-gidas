import json

from cryptography.fernet import Fernet
from flask import current_app


def cipher():
    key = current_app.config.get("EMAIL_OUTBOX_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Falta configurar el cifrado de notificaciones")
    return Fernet(key.encode("ascii") if isinstance(key, str) else key)


def encrypt_payload(payload):
    return cipher().encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")


def decrypt_payload(payload):
    return json.loads(cipher().decrypt(payload.encode("ascii")))
