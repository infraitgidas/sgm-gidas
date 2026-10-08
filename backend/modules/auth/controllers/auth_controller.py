from flask import Request, Response, g, jsonify, request

from urllib.parse import urlsplit

from flask import current_app

from modules.auth.services.auth_service import AuthService
from modules.shared.controllers.responses import error_response, exception_response
from modules.shared.controllers.responses import paginated_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.exceptions import DomainError, LoginLockedError, ValidationError
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)


class AuthController:

    @staticmethod
    def _require_fields(data, keys):
        if not isinstance(data, dict):
            raise ValidationError("Envíe los datos del formulario e intente nuevamente.")
        labels = {"nombre_usuario": "nombre de usuario", "mail": "correo electrónico", "password": "contraseña"}
        fields = {key: f"Ingrese su {labels[key]}." for key in keys
                  if not isinstance(data.get(key), str) or not data[key].strip()}
        if fields:
            raise ValidationError("Revise los campos indicados.", details={"fields": fields})


    @staticmethod
    def _cookie_options() -> dict:
        return {
            "httponly": current_app.config["REFRESH_COOKIE_HTTPONLY"],
            "secure": current_app.config["REFRESH_COOKIE_SECURE"],
            "samesite": current_app.config["REFRESH_COOKIE_SAMESITE"],
            "path": current_app.config["REFRESH_COOKIE_PATH"],
        }

    @staticmethod
    def _set_refresh_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            current_app.config["REFRESH_COOKIE_NAME"], token,
            max_age=current_app.config["REFRESH_TOKEN_EXPIRATION_MINUTES"] * 60,
            **AuthController._cookie_options(),
        )
        response.headers["Cache-Control"] = "no-store"

    @staticmethod
    def _delete_refresh_cookie(response: Response) -> None:
        response.delete_cookie(
            current_app.config["REFRESH_COOKIE_NAME"],
            **AuthController._cookie_options(),
        )
        response.headers["Cache-Control"] = "no-store"

    @staticmethod
    def _no_store(result):
        response = result[0] if isinstance(result, tuple) else result
        response.headers["Cache-Control"] = "no-store"
        return result

    @staticmethod
    def _normalized_origin(
        value: str | None,
        allow_path: bool = False,
    ) -> str | None:
        if not value:
            return None
        parsed = urlsplit(value.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or (not allow_path and parsed.path not in {"", "/"})
        ):
            return None
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"

    @staticmethod
    def _is_trusted_cookie_request(req: Request) -> bool:
        origin_header = req.headers.get("Origin")
        supplied = AuthController._normalized_origin(origin_header)
        if origin_header is None:
            supplied = AuthController._normalized_origin(
                req.headers.get("Referer"),
                allow_path=True,
            )
        trusted = {
            AuthController._normalized_origin(origin)
            for origin in current_app.config["FRONTEND_URLS"]
        }
        trusted.discard(None)
        return supplied in trusted

    @staticmethod
    def _unexpected_error(status_code: int = 500):
        logger.exception("Error interno en operación de autenticación request_id=%s", getattr(g, "request_id", None))
        return error_response("INTERNAL_ERROR", status_code=500)

    @staticmethod
    def _get_token_from_request(req: Request = None) -> str:
        req = req or request
        auth_header = req.headers.get("Authorization")
        if not auth_header:
            raise ValueError("Token requerido")

        parts = auth_header.split(" ")
        if len(parts) != 2 or not parts[1]:
            raise ValueError("Token invalido")

        return parts[1]

    @staticmethod
    def _get_payload_from_request(req: Request = None) -> dict:
        if (getattr(g, "tenant_request_marker", None)
                == id(request._get_current_object())
                and getattr(g, "current_user_payload", None) is not None):
            return g.current_user_payload

        token = AuthController._get_token_from_request(req)
        return AuthService.verify_token(token)

    @staticmethod
    def _require_admin(payload: dict):
        rol = (g.current_user_rol
               if getattr(g, "tenant_request_marker", None)
               == id(request._get_current_object())
               else payload.get("rol"))
        if rol != "ADMIN":
            raise PermissionError(
                "Acceso denegado. Se requiere rol de administrador."
            )

    @staticmethod
    def _request_metadata(req: Request = None) -> dict:
        req = req or request
        return {
            "user_agent": req.headers.get("User-Agent"),
            "ip_address": req.headers.get("X-Forwarded-For", req.remote_addr),
        }

    @staticmethod
    def primer_usuario():
        try:
            existe = AuthService.existe_primer_usuario()
            return jsonify({"existe": existe}), 200
        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except Exception:
            return AuthController._unexpected_error(500)

    @staticmethod
    def register(req: Request = None) -> Response:
        req = req or request
        data = req.get_json()

        try:
            es_primer_usuario = not AuthService.existe_primer_usuario()

            if not es_primer_usuario:
                try:
                    payload = AuthController._get_payload_from_request(req)
                    AuthController._require_admin(payload)
                except DomainError as error:
                    return AuthController._no_store(exception_response(error, operation="autenticación"))
                except ValueError:
                    return error_response("FORBIDDEN", status_code=403)
                except PermissionError:
                    return error_response("FORBIDDEN", status_code=403)

            AuthController._require_fields(data, ("nombre_usuario", "mail", "password"))
            user = AuthService.register(
                nombre_usuario=data["nombre_usuario"],
                mail=data["mail"],
                password=data["password"],
                rol_id=data.get("rol_id"),
                nombre_apellido=data.get("nombre_apellido"),
                dni=data.get("dni"),
                es_primer_usuario=es_primer_usuario,
                actor_id=int(payload["sub"]) if not es_primer_usuario else None,
            )

            tokens = AuthService.generate_tokens(
                user,
                persist_refresh=True,
                metadata=AuthController._request_metadata(req),
            )

            response = jsonify({
                "mensaje": "Usuario creado exitosamente",
                "usuario": {
                    "id": user.id,
                    "nombre_usuario": user.nombre_usuario,
                    "mail": user.mail,
                    "rol": user.rol.nombre,
                    "primer_login": user.primer_login
                },
                "access_token": tokens["access_token"],
                "access_expires_at": tokens["access_expires_at"],
                "session_expires_at": tokens["session_expires_at"],
                "session_warning_seconds": tokens["session_warning_seconds"],
            })
            AuthController._set_refresh_cookie(response, tokens["refresh_token"])
            return response, 201

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except Exception:
            return AuthController._no_store(AuthController._unexpected_error(400))

    @staticmethod
    def login() -> Response:
        data = request.get_json()

        try:
            AuthController._require_fields(data, ("nombre_usuario", "password"))
            result = AuthService.login(
                nombre_usuario=data["nombre_usuario"],
                password=data["password"],
                metadata=AuthController._request_metadata(request),
            )

            response = jsonify({
                "access_token": result["access_token"],
                "access_expires_at": result["access_expires_at"],
                "session_expires_at": result["session_expires_at"],
                "session_warning_seconds": result["session_warning_seconds"],
                "user": result["user"]
            })
            AuthController._set_refresh_cookie(response, result["refresh_token"])
            return response, 200

        except LoginLockedError as error:
            response, status = exception_response(error, operation="autenticación")
            response.headers["Retry-After"] = str(error.retry_after_seconds)
            return AuthController._no_store((response, status))
        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except Exception:
            return AuthController._no_store(AuthController._unexpected_error(401))

    @staticmethod
    def perfil(req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            user_id = int(payload["sub"])
            user = AuthService.get_user_by_id(user_id, solo_activos=True)

            return jsonify(user.serialize()), 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except Exception:
            return AuthController._unexpected_error(401)

    @staticmethod
    def refresh(req: Request = None) -> Response:
        req = req or request
        if not AuthController._is_trusted_cookie_request(req):
            return AuthController._no_store(
                error_response("FORBIDDEN", status_code=403)
            )

        refresh_token = req.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])

        if not refresh_token:
            return AuthController._no_store(
                error_response("AUTH_REQUIRED", status_code=401)
            )

        try:
            tokens = AuthService.refresh_tokens(
                refresh_token,
                metadata=AuthController._request_metadata(req),
            )
            response = jsonify({
                "access_token": tokens["access_token"],
                "access_expires_at": tokens["access_expires_at"],
                "session_expires_at": tokens["session_expires_at"],
                "session_warning_seconds": tokens["session_warning_seconds"],
                "user": tokens["user"],
            })
            AuthController._set_refresh_cookie(response, tokens["refresh_token"])
            return response, 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except Exception:
            return AuthController._no_store(AuthController._unexpected_error(401))

    @staticmethod
    def logout(req: Request = None) -> Response:
        req = req or request
        refresh_token = req.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
        response = jsonify({"mensaje": "Sesion cerrada exitosamente"})

        if not AuthController._is_trusted_cookie_request(req):
            return AuthController._no_store(
                error_response("FORBIDDEN", status_code=403)
            )

        try:
            if refresh_token:
                AuthService.revoke_refresh_token(refresh_token, reason="logout")
        except Exception:
            logger.warning("No se pudo revocar la sesion durante logout")

        AuthController._delete_refresh_cookie(response)
        return response, 200

    @staticmethod
    def change_password(req: Request = None) -> Response:
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            user_id = int(payload["sub"])

            data = req.get_json()
            if not isinstance(data, dict):
                raise ValidationError("Envíe los datos del formulario e intente nuevamente.")
            password_actual = data.get("password_actual")
            password_nueva = data.get("password_nueva")
            password_confirmacion = data.get("password_confirmacion")

            if not password_nueva or not password_confirmacion:
                return error_response("VALIDATION_ERROR", details={"fields": {"password_nueva": "Ingrese la nueva contraseña.", "password_confirmacion": "Confirme la nueva contraseña."}}, status_code=400)

            if password_nueva != password_confirmacion:
                return error_response("VALIDATION_ERROR", details={"fields": {"password_confirmacion": "La confirmación debe coincidir con la nueva contraseña."}}, status_code=400)

            if len(password_nueva) < 6:
                return error_response("VALIDATION_ERROR", details={"fields": {"password_nueva": "La contraseña debe tener al menos 6 caracteres."}}, status_code=400)

            user = AuthService.get_user_by_id(user_id)
            es_primer_cambio = user.primer_login

            if not es_primer_cambio and not password_actual:
                return error_response("VALIDATION_ERROR", details={"fields": {"password_actual": "Ingrese su contraseña actual."}}, status_code=400)

            updated_user = AuthService.change_password(
                user_id=user_id,
                password_actual=password_actual,
                password_nueva=password_nueva,
                es_primer_cambio=es_primer_cambio
            )
            tokens = AuthService.generate_tokens(updated_user, persist_refresh=True, metadata=AuthController._request_metadata(req))
            response = jsonify({
                "mensaje": "Contrasena actualizada exitosamente",
                "access_token": tokens["access_token"],
                "access_expires_at": tokens["access_expires_at"],
                "session_expires_at": tokens["session_expires_at"],
                "session_warning_seconds": tokens["session_warning_seconds"],
                "user": {
                    "id": updated_user.id,
                    "nombre_usuario": updated_user.nombre_usuario,
                    "mail": updated_user.mail,
                    "rol": updated_user.rol.nombre,
                    "primer_login": updated_user.primer_login,
                },
            })
            AuthController._set_refresh_cookie(response, tokens["refresh_token"])
            return response, 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except Exception:
            return AuthController._unexpected_error(400)

    @staticmethod
    def delete_user(user_id: int, req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            current_user_id = int(payload["sub"])

            AuthService.delete_user(
                user_id=user_id,
                current_user_id=current_user_id
            )

            return jsonify({"mensaje": "Usuario eliminado exitosamente"}), 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except Exception:
            return AuthController._unexpected_error(400)

    @staticmethod
    def get_all_users(req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            AuthController._require_admin(payload)

            if pagination_requested(req.args):
                try:
                    params = parse_pagination_params(req.args)
                except ValueError as exc:
                    return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
                users, total = AuthService.get_users_page(
                    params["page"], params["per_page"], params["orden"]
                )
                return paginated_response(
                    [user.serialize() for user in users], params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )

            users = AuthService.get_all_users()
            return jsonify([user.serialize() for user in users]), 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except PermissionError:
            return error_response("FORBIDDEN", status_code=403)
        except Exception:
            return AuthController._unexpected_error(400)

    @staticmethod
    def get_user_by_id(user_id: int, req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            if payload.get("rol") != "ADMIN" and int(payload["sub"]) != user_id:
                return error_response("FORBIDDEN", status_code=403)

            user = AuthService.get_user_by_id(user_id)
            return jsonify(user.serialize()), 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except Exception:
            return AuthController._unexpected_error(404)

    @staticmethod
    def update_user(user_id: int, req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            current_user_id = int(payload["sub"])

            if payload.get("rol") != "ADMIN" and current_user_id != user_id:
                return error_response("FORBIDDEN", status_code=403)

            data = req.get_json()
            if not isinstance(data, dict):
                raise ValidationError("Envíe los datos del formulario e intente nuevamente.")

            if payload.get("rol") != "ADMIN" and (
                "rol_id" in data or "activo" in data
            ):
                return error_response("FORBIDDEN", status_code=403)

            user = AuthService.update_user(user_id, data, current_user_id)

            return jsonify({
                "mensaje": "Usuario actualizado exitosamente",
                "usuario": user.serialize()
            }), 200

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except Exception:
            return AuthController._unexpected_error(400)

    @staticmethod
    def create_user(req: Request = None):
        req = req or request
        try:
            payload = AuthController._get_payload_from_request(req)
            AuthController._require_admin(payload)

            data = req.get_json()
            if not isinstance(data, dict):
                raise ValidationError("Envíe los datos del formulario e intente nuevamente.")

            AuthController._require_fields(data, ("nombre_usuario", "mail", "password"))

            if not data.get("rol_id"):
                return error_response("VALIDATION_ERROR", details={"fields": {"rol_id": "Seleccione un rol disponible."}}, status_code=400)

            if len(data.get("password", "")) < 6:
                return error_response("VALIDATION_ERROR", details={"fields": {"password": "La contraseña debe tener al menos 6 caracteres."}}, status_code=400)

            rol = AuthService.get_rol_by_id(data["rol_id"])
            if not rol:
                return error_response("VALIDATION_ERROR", details={"fields": {"rol_id": "Seleccione un rol disponible."}}, status_code=400)

            user = AuthService.register(
                nombre_usuario=data["nombre_usuario"],
                mail=data["mail"],
                password=data["password"],
                rol_id=data["rol_id"],
                nombre_apellido=data.get("nombre_apellido", data["nombre_usuario"]),
                dni=data.get("dni", 0),
                es_primer_usuario=False,
                actor_id=int(payload["sub"]),
            )

            return jsonify({
                "mensaje": "Usuario creado exitosamente",
                "usuario": user.serialize()
            }), 201

        except DomainError as error:
            return AuthController._no_store(exception_response(error, operation="autenticación"))
        except ValueError as ve:
            return error_response("AUTH_REQUIRED", status_code=401)
        except PermissionError:
            return error_response("FORBIDDEN", status_code=403)
        except Exception:
            return AuthController._unexpected_error(400)
