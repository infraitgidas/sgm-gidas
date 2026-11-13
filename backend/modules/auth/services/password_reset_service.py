"""Solicitudes de un solo uso; ninguna operacion publica revela la cuenta."""
import datetime as dt
import hashlib
import hmac
import html
import secrets
import uuid

from flask import current_app
from sqlalchemy import func, text

from extension import db
from modules.auth.models.password_reset_request import PasswordResetRequest
from modules.auth.models.usuario import Usuario
from modules.auth.services.credentials_policy import normalize_email, validate_password
from modules.notifications.models.email_outbox import EmailOutbox
from modules.notifications.services.payload_cipher import encrypt_payload
from modules.shared.exceptions import DomainError, NotFoundError, ValidationError
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)
REQUEST_MESSAGE = "Si el correo corresponde a una cuenta habilitada, recibirá instrucciones para restablecer la contraseña. Revise también la carpeta de correo no deseado."
INVALID_MESSAGE = "El enlace no es válido o ya no está disponible. Solicite uno nuevo para continuar."


class InvalidPasswordResetToken(DomainError):
    code = "INVALID_PASSWORD_RESET_TOKEN"
    status_code = 400

    def __init__(self):
        super().__init__(INVALID_MESSAGE)


def fingerprint(value, purpose="email"):
    key = current_app.config.get("PASSWORD_RESET_HMAC_KEY")
    if not key:
        raise RuntimeError("Falta configurar la huella de recuperacion")
    return hmac.new(key.encode("utf-8"), f"{purpose}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def lock_user(user_id):
    # Todas las transiciones respetan el mismo orden: usuario, solicitud, mensaje.
    return Usuario.query.filter_by(id=user_id).populate_existing().with_for_update().first()


def begin_sqlite_write():
    # Equivalente serializado para pruebas SQLite; PostgreSQL usa bloqueos de fila.
    if db.engine.dialect.name == "sqlite" and not db.session().in_transaction():
        db.session.execute(text("BEGIN IMMEDIATE"))


def cancel_user_requests(user_id, now=None):
    now = now or dt.datetime.utcnow()
    requests = PasswordResetRequest.query.filter_by(user_id=user_id, consumed_at=None, revoked_at=None).with_for_update().all()
    for reset in requests:
        reset.revoked_at = now
        if reset.email_message_id:
            message = EmailOutbox.query.filter_by(id=reset.email_message_id).with_for_update().first()
            if message and message.status in ("pending", "processing"):
                message.status = "cancelled"
                message.payload_encrypted = None
                message.locked_at = message.locked_by = None
                message.updated_at = now
    db.session.flush()


class PasswordResetService:
    @staticmethod
    def _enqueue(user, ip, requested_by_admin_id=None):
        now = dt.datetime.utcnow()
        cancel_user_requests(user.id, now)
        token = secrets.token_urlsafe(32)
        link = f'{current_app.config["PASSWORD_RESET_PUBLIC_URL"]}#token={token}'
        safe_link = html.escape(link, quote=True)
        payload = {
            "to": user.mail,
            "subject": "GIDAS: restablecer contraseña",
            "text": f"Se solicitó restablecer su contraseña en GIDAS.\n\n{link}\n\nEl enlace es de un solo uso y vence 30 minutos después del envío. Si no lo solicitó, ignore este correo.",
            "html": f'<p>Se solicitó restablecer su contraseña en GIDAS.</p><p><a href="{safe_link}">Restablecer contraseña</a></p><p>El enlace es de un solo uso y vence 30 minutos después del envío. Si no lo solicitó, ignore este correo.</p>',
        }
        message = EmailOutbox(id=uuid.uuid4(), message_type="password_reset", status="pending",
                              payload_encrypted=encrypt_payload(payload), next_attempt_at=now)
        reset = PasswordResetRequest(id=uuid.uuid4(), user_id=user.id,
                                     token_hash=hashlib.sha256(token.encode("ascii")).hexdigest(),
                                     requested_at=now, requested_ip_hmac=fingerprint(ip or "unknown", "ip"),
                                     requested_by_admin_id=requested_by_admin_id, email_message_id=message.id)
        db.session.add(message)
        db.session.flush()
        db.session.add(reset)
        db.session.commit()
        # Solo IDs operativos; nunca destinatario, cuerpo, password o token.
        logger.info("password_reset_queued request=%s message=%s admin=%s", reset.id, message.id, requested_by_admin_id)

    @staticmethod
    def request_public(email, ip):
        email = normalize_email(email, "email")
        try:
            begin_sqlite_write()
            user = Usuario.query.filter(func.lower(func.trim(Usuario.mail)) == email,
                                        Usuario.activo.is_(True), Usuario.deleted_at.is_(None)).with_for_update().first()
            if user:
                PasswordResetService._enqueue(user, ip)
            else:
                db.session.rollback()
        except Exception as error:
            db.session.rollback()
            logger.error("password_reset_request_failed class=%s", type(error).__name__)
        return REQUEST_MESSAGE

    @staticmethod
    def request_admin(user_id, admin_id, ip):
        begin_sqlite_write()
        user = lock_user(user_id)
        if not user or not user.activo or user.deleted_at:
            raise NotFoundError("Usuario no encontrado.")
        PasswordResetService._enqueue(user, ip, admin_id)

    @staticmethod
    def confirm(token, password, confirmation):
        validate_password(password, "password_nueva")
        if not isinstance(confirmation, str) or confirmation != password:
            raise ValidationError("Revise la confirmación.", details={"fields": {"password_confirmacion": "La confirmación debe coincidir con la nueva contraseña."}})
        if not isinstance(token, str) or len(token) != 43 or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for c in token):
            raise InvalidPasswordResetToken()
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        begin_sqlite_write()
        # Buscar el usuario antes de bloquear mantiene el orden de locks del worker.
        candidate = PasswordResetRequest.query.filter_by(token_hash=token_hash).first()
        if not candidate:
            raise InvalidPasswordResetToken()
        user = lock_user(candidate.user_id)
        reset = PasswordResetRequest.query.filter_by(id=candidate.id).populate_existing().with_for_update().first()
        now = dt.datetime.utcnow()
        if (not reset or reset.revoked_at or reset.consumed_at or not reset.activated_at
                or not reset.expires_at or reset.expires_at <= now
                or not user or not user.activo or user.deleted_at):
            raise InvalidPasswordResetToken()
        from modules.auth.services.auth_service import AuthService
        user.set_password(password)
        user.primer_login = False
        user.mark_updated()
        reset.consumed_at = now
        AuthService.revoke_user_refresh_tokens(user.id, "password_reset")
        # No modifica bloqueos de login activos; conservan su vencimiento (ISS-78).
        db.session.commit()
        logger.info("password_reset_consumed request=%s", reset.id)
