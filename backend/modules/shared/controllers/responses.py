from math import ceil

from flask import g, has_request_context, jsonify

from modules.shared.exceptions import DomainError
from modules.shared.services.logging_config import get_logger
from modules.shared.services.error_messages import public_message


logger = get_logger(__name__)


DEFAULT_ERROR_MESSAGES = {
    "VALIDATION_ERROR": (
        "Lo sentimos, no pudimos guardar los cambios. "
        "Verifique los datos e intente nuevamente."
    ),
    "AUTH_REQUIRED": "Lo sentimos, debe iniciar sesión para continuar.",
    "LOGIN_LOCKED": "Lo sentimos, se alcanzó el límite de intentos. Intente nuevamente en 15 minutos.",
    "FORBIDDEN": "Lo sentimos, no tiene permisos para realizar esta acción.",
    "NOT_FOUND": "Lo sentimos, no pudimos encontrar la información solicitada.",
    "CONFLICT": (
        "Lo sentimos, la operación entra en conflicto con el estado actual. "
        "Revise la información e intente nuevamente."
    ),
    "RATE_LIMIT_EXCEEDED": (
        "Lo sentimos, recibimos demasiadas solicitudes. "
        "Intente nuevamente en unos minutos."
    ),
    "REQUEST_TOO_LARGE": (
        "Lo sentimos, la solicitud supera el tamaño permitido. "
        "Reduzca el contenido e intente nuevamente."
    ),
    "UNSUPPORTED_MEDIA_TYPE": (
        "Lo sentimos, el formato de la solicitud no es compatible. "
        "Envíe la información como JSON e intente nuevamente."
    ),
    "HTTP_ERROR": (
        "Lo sentimos, no pudimos completar la solicitud. "
        "Revise la información e intente nuevamente."
    ),
    "INTERNAL_ERROR": (
        "Lo sentimos, no pudimos completar la operación. "
        "Intente nuevamente."
    ),
    "SERVICE_UNAVAILABLE": "Lo sentimos, el servicio no está disponible temporalmente. Intente nuevamente.",
}


def success_response(data=None, meta=None, status_code=200):
    payload = {
        "data": data,
        "meta": meta or {},
        "error": None,
    }
    return jsonify(payload), status_code


def paginated_response(data, page, per_page, total, meta=None, status_code=200):
    total_pages = max(1, ceil(total / per_page)) if per_page else 1
    pagination_meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }
    if meta:
        pagination_meta.update(meta)

    return success_response(data=data, meta=pagination_meta, status_code=status_code)


def error_response(code, message=None, details=None, status_code=400):
    fallback = DEFAULT_ERROR_MESSAGES.get(code, DEFAULT_ERROR_MESSAGES["INTERNAL_ERROR"])
    if code == "AUTH_REQUIRED" and message and (message.startswith(("Refresh token", "Token")) or message == "Usuario no encontrado"):
        message = fallback
    safe_message = public_message(message or fallback, fallback)
    safe_details = {}
    fields = (details or {}).get("fields")
    if isinstance(fields, dict):
        fields = {
            key: public_message(value, "Revise este campo e intente nuevamente.")
            for key, value in fields.items() if isinstance(key, str) and isinstance(value, str)
        }
    if fields:
        safe_details["fields"] = fields
        safe_message = "Revise los campos indicados e intente nuevamente."
    if code == "INTERNAL_ERROR":
        safe_message = fallback
        safe_details = {}
    if has_request_context() and getattr(g, "request_id", None):
        safe_details["request_id"] = g.request_id
    # Readiness exposes only its documented dependency states, never exception details.
    if isinstance((details or {}).get("dependencies"), dict):
        safe_details["dependencies"] = {
            key: value for key, value in details["dependencies"].items()
            if key in {"database", "redis"} and value in {"ok", "unavailable"}
        }
    payload = {
        "data": None,
        "error": {
            "code": code,
            "message": safe_message,
            "details": safe_details,
        },
    }
    return jsonify(payload), status_code


def exception_response(error: Exception, *, operation: str):
    if isinstance(error, DomainError):
        return error_response(
            error.code,
            message=error.message,
            details=error.details,
            status_code=error.status_code,
        )

    logger.error(
        "Error interno durante %s exception_type=%s request_id=%s",
        operation,
        type(error).__name__,
        getattr(g, "request_id", None),
    )
    request_id = getattr(g, "request_id", None)
    details = {"request_id": request_id} if request_id else {}
    return error_response(
        "INTERNAL_ERROR",
        details=details,
        status_code=500,
    )
