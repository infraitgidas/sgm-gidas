"""Validación del enlace opcional de trabajos; nunca se consulta la URL."""
from urllib.parse import urlsplit
import re
from ipaddress import IPv6Address

from modules.shared.exceptions import ValidationError

MAX_ENLACE = 2048


def validar_enlace(valor):
    if valor is None:
        return None
    mensaje = "Ingrese un enlace HTTP o HTTPS válido, de hasta 2048 caracteres."
    def rechazar():
        raise ValidationError(mensaje, details={"fields": {"enlace": mensaje}})
    if not isinstance(valor, str):
        rechazar()
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > MAX_ENLACE or re.search(r"[\s\x00-\x1f\x7f\\]", valor):
        rechazar()
    try:
        partes = urlsplit(valor)
        if partes.scheme.lower() not in ("http", "https") or not partes.hostname or partes.username is not None or partes.password is not None:
            rechazar()
        host = partes.hostname
        if ":" in host:
            IPv6Address(host)
        elif not re.fullmatch(r"[A-Za-z0-9.-]+", host.encode("idna").decode("ascii")):
            rechazar()
        partes.port  # Valida también puertos inválidos.
    except (ValueError, UnicodeError):
        rechazar()
    return valor
