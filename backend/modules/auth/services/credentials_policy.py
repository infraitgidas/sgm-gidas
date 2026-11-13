"""Reglas de identidad compartidas por altas, ediciones y recuperacion."""
import re

from modules.shared.exceptions import ValidationError


def normalize_email(value, field="mail"):
    email = value.strip().lower() if isinstance(value, str) else ""
    if len(email) > 120 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValidationError("Revise el correo electrónico.", details={"fields": {field: "Ingrese un correo electrónico válido."}})
    return email


def validate_password(value, field="password"):
    if not isinstance(value, str) or len(value) < 6:
        raise ValidationError("Revise la contraseña.", details={"fields": {field: "Ingrese una contraseña de al menos 6 caracteres."}})
    # bcrypt admite hasta 72 bytes, no 72 caracteres Unicode.
    if len(value.encode("utf-8")) > 72:
        raise ValidationError("Revise la contraseña.", details={"fields": {field: "La contraseña es demasiado larga. Use hasta 72 bytes."}})
    return value
