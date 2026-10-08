"""Resolve the single loaded UCT from the authenticated user's memberships."""

from flask import g, request

from extension import db
from modules.auth.models.usuario import Usuario
from modules.auth.services.auth_service import AuthService
from modules.auth.services.uct_membership_service import single_allowed_uct_id
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.controllers.responses import error_response


PUBLIC_AUTH_PATHS = {
    "/api/v1/auth/primer-usuario",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}
AUTH_WITHOUT_MEMBERSHIP = {
    "/api/v1/auth/perfil",
    "/api/v1/auth/cambiar-password",
    "/api/v1/auth/ucts-permitidas",
}


def register_tenant_request_scope(app):
    @app.before_request
    def resolve_tenant_request():
        g.current_grupo_utn_id = None
        g.tenant_request_marker = None
        if request.method == "OPTIONS" or not request.path.startswith("/api/v1/"):
            return None
        path = request.path.rstrip("/")
        if path.startswith("/api/v1/health") or path in PUBLIC_AUTH_PATHS:
            return None
        if path == "/api/v1/auth/register" and not AuthService.existe_primer_usuario():
            return None
        if request.endpoint is None:
            return None

        authorization = request.headers.get("Authorization", "")
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            return error_response("AUTH_REQUIRED", status_code=401)
        try:
            payload = AuthService.verify_token(parts[1])
            user = db.session.get(Usuario, int(payload["sub"]))
        except Exception:
            return error_response("AUTH_REQUIRED", status_code=401)
        if user is None or not user.activo or user.deleted_at is not None:
            return error_response("AUTH_REQUIRED", status_code=401)

        g.current_user_payload = payload
        g.current_user_id = user.id
        g.current_user_rol = user.rol.nombre
        g.tenant_request_marker = id(request._get_current_object())

        group_id = single_allowed_uct_id(user.id)
        if group_id is not None:
            # Clear objects loaded while resolving membership. A later
            # Session.get must issue a scoped query even when an app context
            # is reused by tests or background request wrappers.
            db.session.remove()
            g.current_grupo_utn_id = group_id
            return None

        if path in AUTH_WITHOUT_MEMBERSHIP:
            return None
        if path == "/api/v1/grupo/grupo-utn" and request.method == "POST" and user.rol.nombre == "ADMIN":
            if not GrupoInvestigacionUtn.query.filter(
                GrupoInvestigacionUtn.activo.is_(True),
                GrupoInvestigacionUtn.deleted_at.is_(None),
            ).first():
                g.creando_primera_uct = True
                return None

        return error_response(
            "FORBIDDEN",
            message="Lo sentimos, su usuario no tiene una UCT activa asignada. Solicite acceso al administrador.",
            status_code=403,
        )
