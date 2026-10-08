from functools import wraps

from flask import g, request

from modules.auth.services.auth_service import AuthService
from modules.shared.controllers.responses import error_response


def _authenticate_request():
    if (getattr(g, "tenant_request_marker", None)
            == id(request._get_current_object())
            and getattr(g, "current_user_payload", None) is not None):
        return g.current_user_payload, None
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None, error_response("AUTH_REQUIRED", status_code=401)

    parts = auth_header.split(" ")

    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None, error_response(
            "AUTH_REQUIRED",
            message="Lo sentimos, el formato del token no es valido. Inicie sesion nuevamente.",
            status_code=401,
        )

    try:
        payload = AuthService.verify_token(parts[1])
        g.current_user_payload = payload
        g.current_user_id = int(payload["sub"])
        g.current_user_rol = payload.get("rol")
        return payload, None
    except Exception:
        return None, error_response("AUTH_REQUIRED", status_code=401)


def requiere_auth(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        _, auth_error_response = _authenticate_request()
        if auth_error_response:
            return auth_error_response

        return func(*args, **kwargs)

    return wrapper


def requiere_rol(*roles_permitidos):
    roles_permitidos = [r.upper() for r in roles_permitidos]

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            _, auth_error_response = _authenticate_request()
            if auth_error_response:
                return auth_error_response

            if not g.current_user_rol:
                return error_response("FORBIDDEN", status_code=403)

            if g.current_user_rol.upper() not in roles_permitidos:
                return error_response("FORBIDDEN", status_code=403)

            return func(*args, **kwargs)

        return wrapper

    return decorator
