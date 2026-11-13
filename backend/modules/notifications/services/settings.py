import base64
from urllib.parse import urlsplit


def validate_email_settings(config, required=False):
    production = config.get("APP_ENV") in {"production", "prod", "staging", "preproduction"}
    if not required and not production:
        return
    required_fields = ("MAIL_SERVER", "MAIL_DEFAULT_SENDER", "PASSWORD_RESET_PUBLIC_URL", "EMAIL_OUTBOX_ENCRYPTION_KEY", "PASSWORD_RESET_HMAC_KEY")
    if any(not config.get(key) for key in required_fields):
        raise RuntimeError("Configure SMTP, URL publica y secretos de recuperacion antes de habilitar el servicio")
    key = config["EMAIL_OUTBOX_ENCRYPTION_KEY"]
    try:
        if len(base64.b64decode(key, altchars=b"-_", validate=True)) != 32:
            raise ValueError()
    except (ValueError, TypeError):
        raise RuntimeError("EMAIL_OUTBOX_ENCRYPTION_KEY debe ser una clave Fernet valida") from None
    hmac_key = config["PASSWORD_RESET_HMAC_KEY"]
    if len(hmac_key) < 32:
        raise RuntimeError("PASSWORD_RESET_HMAC_KEY debe tener al menos 32 caracteres")
    secrets = [config.get(name) for name in ("SECRET_KEY", "JWT_SECRET", "REFRESH_SECRET")]
    if key == hmac_key or key in secrets or hmac_key in secrets:
        raise RuntimeError("Los secretos de recuperacion deben ser independientes")
    mode = config.get("SMTP_TLS_MODE")
    if mode not in {"none", "ssl", "starttls"} or production and mode == "none":
        raise RuntimeError("SMTP_TLS_MODE debe usar starttls o ssl fuera de desarrollo")
    timeout = config.get("SMTP_TIMEOUT_SECONDS", 20)
    if not isinstance(timeout, int) or not 1 <= timeout <= 60:
        raise RuntimeError("SMTP_TIMEOUT_SECONDS debe estar entre 1 y 60 segundos")
    public = urlsplit(config["PASSWORD_RESET_PUBLIC_URL"])
    if (public.scheme not in ({"https"} if production else {"http", "https"}) or not public.hostname
            or public.username or public.password or public.fragment or public.query
            or not public.path.rstrip("/").endswith("/restablecer-password")):
        raise RuntimeError("PASSWORD_RESET_PUBLIC_URL debe ser una URL de restablecimiento valida sin query ni fragmento")
    if production:
        allowed = [urlsplit(origin) for origin in config.get("FRONTEND_URLS", [])]
        if not any((origin.scheme, origin.netloc) == (public.scheme, public.netloc) for origin in allowed):
            raise RuntimeError("La URL publica debe pertenecer a un frontend autorizado")
