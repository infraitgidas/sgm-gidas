import functools
import hashlib
import hmac

from flask import current_app, g, request

from extension import db
from modules.auth.services.password_reset_service import PasswordResetService, fingerprint
from modules.shared.controllers.responses import error_response, exception_response, success_response
from modules.shared.exceptions import DomainError
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)


def email_rate_key():
    data = request.get_json(silent=True)
    email = data.get("email", "") if isinstance(data, dict) else ""
    email = email[:500].strip().lower() if isinstance(email, str) else "invalid"
    try:
        return fingerprint(email)
    except RuntimeError:
        # Sin configurar no se entregan correos; aun se aplica un limite opaco.
        secret = current_app.config["SECRET_KEY"]
        return hmac.new(secret.encode("utf-8"), email.encode("utf-8"), hashlib.sha256).hexdigest()


def no_store(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        result = view(*args, **kwargs)
        response = result[0] if isinstance(result, tuple) else result
        response.headers["Cache-Control"] = "no-store"
        return result
    return wrapped


class PasswordResetController:
    @staticmethod
    @no_store
    def request_public():
        data = request.get_json(silent=True)
        try:
            message = PasswordResetService.request_public(data.get("email") if isinstance(data, dict) else None, request.remote_addr)
            return success_response({"message": message}, status_code=202)
        except DomainError as error:
            db.session.rollback()
            return exception_response(error, operation="recuperar la contraseña")

    @staticmethod
    @no_store
    def confirm():
        data = request.get_json(silent=True)
        data = data if isinstance(data, dict) else {}
        try:
            PasswordResetService.confirm(data.get("token"), data.get("password_nueva"), data.get("password_confirmacion"))
            return success_response({"message": "Contraseña actualizada con éxito. Inicie sesión con su nueva contraseña."})
        except DomainError as error:
            db.session.rollback()
            return exception_response(error, operation="restablecer la contraseña")
        except Exception as error:
            db.session.rollback()
            logger.error("password_reset_confirm_failed class=%s", type(error).__name__)
            return error_response("INTERNAL_ERROR", status_code=500)

    @staticmethod
    @no_store
    def request_admin(user_id):
        try:
            PasswordResetService.request_admin(user_id, g.current_user_id, request.remote_addr)
            return success_response({"message": "Se solicitó el envío del enlace de restablecimiento al correo del usuario."}, status_code=202)
        except DomainError as error:
            db.session.rollback()
            return exception_response(error, operation="solicitar la recuperación")
        except Exception as error:
            db.session.rollback()
            logger.error("password_reset_admin_failed class=%s", type(error).__name__)
            return error_response("SERVICE_UNAVAILABLE", status_code=503)
