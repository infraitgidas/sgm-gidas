import jwt
import datetime
import hashlib
import hmac
import math
import uuid
import bcrypt
from flask import current_app
from sqlalchemy import text
from modules.auth.models.persona import Persona
from modules.auth.models.login_attempt import LoginAttempt
from modules.auth.models.refresh_token_session import RefreshTokenSession
from modules.auth.models.usuario import Usuario, RolUsuario
from extension import db
from config import Config
from modules.shared.exceptions import AuthenticationError, ConflictError, LoginLockedError, NotFoundError, ValidationError
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"unused-login-secret", bcrypt.gensalt())
_LOGIN_FAILURE_MESSAGE = 'Lo sentimos, no pudimos iniciar sesión. Verifique su usuario y contraseña e intente nuevamente.'
_LOGIN_LOCK_MINUTES = 15
_LOGIN_MAX_FAILURES = 3


class AuthService:

    @staticmethod
    def _access_token_expires_at() -> datetime.datetime:
        return datetime.datetime.utcnow() + datetime.timedelta(
            minutes=Config.JWT_EXPIRATION_MINUTES
        )

    @staticmethod
    def _refresh_token_expires_at() -> datetime.datetime:
        return datetime.datetime.utcnow() + datetime.timedelta(
            minutes=Config.REFRESH_TOKEN_EXPIRATION_MINUTES
        )

    @staticmethod
    def _hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _request_metadata(metadata: dict | None = None) -> dict:
        metadata = metadata or {}
        return {
            "user_agent": (metadata.get("user_agent") or "")[:255] or None,
            "ip_address": (metadata.get("ip_address") or "")[:45] or None,
        }

    @staticmethod
    def _with_optional_audience(payload: dict) -> dict:
        if Config.JWT_AUDIENCE:
            return {**payload, "aud": Config.JWT_AUDIENCE}
        return payload

    @staticmethod
    def _decode_access_token(token: str) -> dict:
        decode_kwargs = {
            "issuer": Config.JWT_ISSUER,
            "algorithms": [Config.JWT_ALGORITHM],
        }

        if Config.JWT_AUDIENCE:
            decode_kwargs["audience"] = Config.JWT_AUDIENCE
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        return jwt.decode(token, Config.JWT_SECRET, **decode_kwargs)

    @staticmethod
    def _decode_refresh_token(token: str) -> dict:
        return jwt.decode(
            token,
            Config.REFRESH_SECRET,
            issuer=Config.JWT_ISSUER,
            algorithms=[Config.JWT_ALGORITHM],
            options={"verify_aud": False},
        )

    @staticmethod
    def _get_user_or_error(user_id: int, solo_activos: bool = False) -> Usuario:
        user = db.session.get(Usuario, user_id)

        if not user:
            raise NotFoundError('Usuario no encontrado')

        if solo_activos and (not user.activo or user.deleted_at is not None):
            raise NotFoundError('Usuario no encontrado')

        return user

    @staticmethod
    def _generate_access_token(
        user: Usuario,
        expires_at: datetime.datetime | None = None,
    ) -> str:
        expires_at = expires_at or AuthService._access_token_expires_at()
        access_payload = AuthService._with_optional_audience({
            "sub": str(user.id),
            "nombre_usuario": user.nombre_usuario,
            "rol": user.rol.nombre,   
            "exp": expires_at,
            "iss": Config.JWT_ISSUER
        })

        return jwt.encode(
            access_payload,
            Config.JWT_SECRET,
            algorithm=Config.JWT_ALGORITHM
        )

    @staticmethod
    def _generate_refresh_token(user: Usuario) -> tuple[str, str, datetime.datetime]:
        jti = str(uuid.uuid4())
        expires_at = AuthService._refresh_token_expires_at()
        refresh_payload = {
            "sub": str(user.id),
            "jti": jti,
            "exp": expires_at,
            "iss": Config.JWT_ISSUER
        }

        refresh_token = jwt.encode(
            refresh_payload,
            Config.REFRESH_SECRET,
            algorithm=Config.JWT_ALGORITHM
        )

        return refresh_token, jti, expires_at

    @staticmethod
    def _store_refresh_session(
        user: Usuario,
        refresh_token: str,
        jti: str,
        expires_at: datetime.datetime,
        metadata: dict | None = None,
    ) -> RefreshTokenSession:
        request_metadata = AuthService._request_metadata(metadata)
        session = RefreshTokenSession(
            user_id=user.id,
            token_hash=AuthService._hash_refresh_token(refresh_token),
            jti=jti,
            expires_at=expires_at,
            user_agent=request_metadata["user_agent"],
            ip_address=request_metadata["ip_address"],
        )
        db.session.add(session)
        db.session.flush()
        return session

    @staticmethod
    def _claim_refresh_session(
        session_id: int,
        claimed_at: datetime.datetime,
    ) -> bool:
        updated = RefreshTokenSession.query.filter(
            RefreshTokenSession.id == session_id,
            RefreshTokenSession.revoked_at.is_(None),
            RefreshTokenSession.expires_at > claimed_at,
        ).update(
            {
                RefreshTokenSession.revoked_at: claimed_at,
                RefreshTokenSession.revoked_reason: "rotating",
            },
            synchronize_session="fetch",
        )
        return updated == 1

    @staticmethod
    def generate_tokens(
        user: Usuario,
        persist_refresh: bool = False,
        metadata: dict | None = None,
    ) -> dict:
        access_expires_at = AuthService._access_token_expires_at()
        access_token = AuthService._generate_access_token(user, access_expires_at)
        refresh_token, jti, expires_at = AuthService._generate_refresh_token(user)

        if persist_refresh:
            try:
                AuthService._store_refresh_session(
                    user,
                    refresh_token,
                    jti,
                    expires_at,
                    metadata,
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise Exception("Error al registrar la sesion de usuario")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_expires_at": access_expires_at.isoformat() + "Z",
            "session_expires_at": expires_at.isoformat() + "Z",
            "session_warning_seconds": Config.SESSION_WARNING_SECONDS,
        }

    # -------------------------
    # Verificar si existe primer usuario
    # -------------------------
    @staticmethod
    def existe_primer_usuario() -> bool:
        """Verifica si existe al menos un usuario en el sistema"""
        return Usuario.query.first() is not None

    # -------------------------
    # Login
    # -------------------------
    @staticmethod
    def _login_identifier_hash(nombre_usuario: str) -> str:
        secret = current_app.config.get("SECRET_KEY") or Config.SECRET_KEY
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        return hmac.new(secret, nombre_usuario.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _lock_login_attempt(nombre_usuario: str, now: datetime.datetime) -> LoginAttempt:
        identifier_hash = AuthService._login_identifier_hash(nombre_usuario)
        # SQLite has no SELECT FOR UPDATE; BEGIN IMMEDIATE serializes its test/local writes.
        if db.engine.dialect.name == "sqlite":
            db.session.execute(text("BEGIN IMMEDIATE"))
        db.session.execute(
            text("""
                INSERT INTO login_attempt
                    (identifier_hash, failed_count, created_at, updated_at)
                VALUES (:identifier_hash, 0, :now, :now)
                ON CONFLICT (identifier_hash) DO NOTHING
            """),
            {"identifier_hash": identifier_hash, "now": now},
        )
        return LoginAttempt.query.filter_by(identifier_hash=identifier_hash).with_for_update().one()

    @staticmethod
    def login(
        nombre_usuario: str,
        password: str,
        metadata: dict | None = None,
    ) -> dict:

        now = datetime.datetime.utcnow()
        nombre_usuario = nombre_usuario.strip()
        attempt = AuthService._lock_login_attempt(nombre_usuario, now)
        now = datetime.datetime.utcnow()

        if attempt.locked_until and attempt.locked_until > now:
            remaining = max(1, math.ceil((attempt.locked_until - now).total_seconds()))
            db.session.rollback()
            raise LoginLockedError(remaining)

        if attempt.locked_until:
            attempt.failed_count = 0
            attempt.locked_until = None

        user = Usuario.query.filter_by(
            nombre_usuario=nombre_usuario,
            activo=True
        ).filter(Usuario.deleted_at.is_(None)).first()
        valid_password = (
            user.verificar_password(password)
            if user else bcrypt.checkpw(password.encode("utf-8"), _DUMMY_PASSWORD_HASH)
        )

        if not user or not valid_password:
            attempt.failed_count += 1
            attempt.last_failed_at = now
            if attempt.failed_count >= _LOGIN_MAX_FAILURES:
                attempt.locked_until = now + datetime.timedelta(minutes=_LOGIN_LOCK_MINUTES)
                identifier_prefix = attempt.identifier_hash[:16]
                db.session.commit()
                logger.info("login_locked identifier_hash_prefix=%s", identifier_prefix)
                raise LoginLockedError(_LOGIN_LOCK_MINUTES * 60)
            db.session.commit()
            raise AuthenticationError(_LOGIN_FAILURE_MESSAGE)

        attempt.failed_count = 0
        attempt.locked_until = None

        tokens = AuthService.generate_tokens(
            user,
            persist_refresh=True,
            metadata=metadata,
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "access_expires_at": tokens["access_expires_at"],
            "session_expires_at": tokens["session_expires_at"],
            "session_warning_seconds": tokens["session_warning_seconds"],
            "user": {
                "id": user.id,
                "nombre_usuario": user.nombre_usuario,
                "mail": user.mail,
                "rol": user.rol.nombre,
                "primer_login": user.primer_login
            }
        }

    # -------------------------
    # Registro
    # -------------------------
    @staticmethod
    def register(
        nombre_usuario: str,
        mail: str,
        password: str,
        rol_id: int | None = None,
        nombre_apellido: str | None = None,
        dni: str | None = None,
        es_primer_usuario: bool = False,
        actor_id: int | None = None,
    ) -> Usuario:
        existe = Usuario.query.filter(
            (Usuario.nombre_usuario == nombre_usuario) |
            (Usuario.mail == mail)
        ).first()

        if existe:
            fields = {}
            if existe.nombre_usuario == nombre_usuario:
                fields["nombre_usuario"] = "El nombre de usuario ya está en uso. Ingrese otro."
            if existe.mail == mail:
                fields["mail"] = "El correo electrónico ya está en uso. Ingrese otro."
            raise ConflictError("Revise los campos indicados.", details={"fields": fields})

        if es_primer_usuario:
            rol = RolUsuario.query.filter_by(nombre="ADMIN").first()
            if not rol:
                raise Exception("Rol ADMIN no encontrado en el sistema")
            primer_login = False
        else:
            primer_login = True
            if not rol_id:
                raise ValidationError('Seleccione un rol e intente nuevamente.', details={"fields": {'rol_id': 'Seleccione un rol para el usuario.'}})
            rol = RolUsuario.query.get(rol_id)
            if not rol:
                raise ValidationError('Seleccione un rol disponible.', details={"fields": {'rol_id': 'Seleccione un rol disponible.'}})

        persona_id = None
        if nombre_apellido and dni:
            persona = Persona(
                nombre_apellido=nombre_apellido,
                dni=dni
            )
            db.session.add(persona)
            db.session.flush()
            persona_id = persona.id

        nuevo_usuario = Usuario(
            nombre_usuario=nombre_usuario,
            mail=mail,
            id_persona=persona_id,
            id_rol=rol.id,
            primer_login=primer_login
        )

        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)

        if not es_primer_usuario and actor_id is not None:
            from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
            from modules.auth.services.uct_membership_service import single_allowed_uct_id

            group_id = single_allowed_uct_id(actor_id)
            if group_id is None:
                raise ValidationError("El administrador debe tener una UCT activa asignada.")
            db.session.flush()
            db.session.add(UsuarioGrupoUtn(
                usuario_id=nuevo_usuario.id,
                grupo_utn_id=group_id,
                created_by=actor_id,
            ))

        try:
            db.session.commit()
            return nuevo_usuario
        except Exception:
            db.session.rollback()
            raise Exception("Error al registrar usuario")        
        
    # -------------------------
    # Refresh token
    # -------------------------
    @staticmethod
    def refresh_tokens(
        refresh_token: str,
        metadata: dict | None = None,
    ) -> dict:
        try:
            payload = AuthService._decode_refresh_token(refresh_token)

            user_id = int(payload["sub"])
            jti = payload.get("jti")
            try:
                user = AuthService._get_user_or_error(user_id, solo_activos=True)
            except NotFoundError as error:
                raise AuthenticationError("Usuario no encontrado") from error
            current_session = RefreshTokenSession.query.filter_by(
                token_hash=AuthService._hash_refresh_token(refresh_token)
            ).first()

            if not current_session:
                raise AuthenticationError('Refresh token invalido')

            if current_session.jti != jti:
                raise AuthenticationError('Refresh token invalido')

            if current_session.user_id != user.id:
                raise AuthenticationError('Refresh token invalido')

            if current_session.is_revoked:
                raise AuthenticationError('Refresh token revocado')

            if current_session.is_expired:
                current_session.revoke("expired")
                db.session.commit()
                raise AuthenticationError('Refresh token expirado')

            claimed_at = datetime.datetime.utcnow()
            if not AuthService._claim_refresh_session(current_session.id, claimed_at):
                db.session.rollback()
                raise AuthenticationError('Refresh token revocado')

            access_expires_at = AuthService._access_token_expires_at()
            access_token = AuthService._generate_access_token(user, access_expires_at)
            new_refresh_token, new_jti, expires_at = AuthService._generate_refresh_token(user)
            new_session = AuthService._store_refresh_session(
                user,
                new_refresh_token,
                new_jti,
                expires_at,
                metadata,
            )
            current_session.revoked_reason = "rotated"
            current_session.replaced_by_id = new_session.id
            db.session.commit()

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "access_expires_at": access_expires_at.isoformat() + "Z",
                "session_expires_at": expires_at.isoformat() + "Z",
                "session_warning_seconds": Config.SESSION_WARNING_SECONDS,
                "user": {
                    "id": user.id,
                    "nombre_usuario": user.nombre_usuario,
                    "mail": user.mail,
                    "rol": user.rol.nombre,
                    "primer_login": user.primer_login,
                },
            }

        except jwt.ExpiredSignatureError:
            raise AuthenticationError('Refresh token expirado')
        except jwt.InvalidTokenError:
            raise AuthenticationError('Refresh token invalido')
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def revoke_refresh_token(refresh_token: str, reason: str = "logout"):
        try:
            payload = AuthService._decode_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return
        except jwt.InvalidTokenError:
            raise AuthenticationError('Refresh token invalido')

        session = RefreshTokenSession.query.filter_by(
            token_hash=AuthService._hash_refresh_token(refresh_token)
        ).first()

        if not session:
            raise AuthenticationError('Refresh token invalido')

        if session.jti != payload.get("jti"):
            raise AuthenticationError('Refresh token invalido')

        if not session.is_revoked:
            session.revoke(reason)
            db.session.commit()

    @staticmethod
    def revoke_user_refresh_tokens(user_id: int, reason: str):
        sessions = RefreshTokenSession.query.filter(
            RefreshTokenSession.user_id == user_id,
            RefreshTokenSession.revoked_at.is_(None),
        ).all()

        for session in sessions:
            session.revoke(reason)


    # -------------------------
    # Verificar token
    # -------------------------
    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            return AuthService._decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError('Token expirado')
        except jwt.InvalidTokenError:
            raise AuthenticationError('Token inválido')

    # -------------------------
    # Cambiar contraseña    
    # -------------------------
        
    @staticmethod
    def change_password(user_id: int, password_actual: str, password_nueva: str, es_primer_cambio: bool = False):
        user = AuthService._get_user_or_error(user_id, solo_activos=True)
        if not password_nueva:
            raise ValidationError('La contraseña nueva es obligatoria', details={"fields": {'password_nueva': 'La contraseña nueva es obligatoria'}})

        if not es_primer_cambio:
            if not isinstance(password_actual, str) or not user.verificar_password(password_actual):
                message = "La contraseña actual es incorrecta. Verifique este campo."
                raise ValidationError(message, details={"fields": {"password_actual": message}})
            user.set_password(password_nueva)
        else:
            user.set_password(password_nueva)

        user.primer_login = False
        AuthService.revoke_user_refresh_tokens(user.id, "password_changed")

        try:
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            raise Exception("Error al cambiar la contraseña")
        
    
    
    @staticmethod
    def delete_user(user_id: int, current_user_id: int):

        user = AuthService._get_user_or_error(user_id, solo_activos=True)
        
        # Evitar que un admin se elimine a sí mismo
        if user_id == current_user_id:
            raise ConflictError('No puede eliminar su propia cuenta')
        
        # Verificar que quede al menos un admin
        if user.rol.nombre == "ADMIN":
            admin_count = Usuario.query.join(RolUsuario).filter(
                RolUsuario.nombre == "ADMIN",
                Usuario.activo == True
            ).count()
            if admin_count <= 1:
                raise ConflictError('Debe quedar al menos un administrador en el sistema')

        user.soft_delete(current_user_id)
        AuthService.revoke_user_refresh_tokens(user.id, "user_deleted")

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise Exception("Error al eliminar usuario")

    # -------------------------
    # CRUD Usuarios
    # -------------------------
    
    @staticmethod
    def get_all_users():
        """Obtener todos los usuarios activos"""
        return Usuario.query.filter(
            Usuario.activo == True,
            Usuario.deleted_at.is_(None)
        ).order_by(Usuario.id.asc()).all()

    @staticmethod
    def get_users_page(page: int, per_page: int, orden: str = "asc"):
        query = Usuario.query.filter(
            Usuario.activo.is_(True),
            Usuario.deleted_at.is_(None),
        )
        total = query.count()
        direction = Usuario.id.desc() if orden == "desc" else Usuario.id.asc()
        users = query.order_by(direction).offset((page - 1) * per_page).limit(per_page).all()
        return users, total
    
    @staticmethod
    def get_user_by_id(user_id: int, solo_activos: bool = False):
        """Obtener un usuario por ID."""
        return AuthService._get_user_or_error(user_id, solo_activos=solo_activos)
    
    @staticmethod
    def update_user(user_id: int, data: dict, current_user_id: int):
        """Actualizar datos de un usuario"""
        user = AuthService._get_user_or_error(user_id, solo_activos=True)
        requested_rol_id = data.get("rol_id")
        requested_rol_name = data.get("rol")
        requested_rol = None

        if requested_rol_id is not None:
            requested_rol = db.session.get(RolUsuario, requested_rol_id)
            if not requested_rol:
                raise ValidationError('Seleccione un rol disponible.', details={"fields": {'rol_id': 'Seleccione un rol disponible.'}})
        elif requested_rol_name is not None:
            requested_rol = RolUsuario.query.filter_by(nombre=requested_rol_name).first()
            if not requested_rol:
                raise ValidationError('Seleccione un rol disponible.', details={"fields": {'rol_id': 'Seleccione un rol disponible.'}})

        changes_role = requested_rol is not None and requested_rol.id != user.id_rol
        
        # Evitar que un admin se desactive a sí mismo
        if user_id == current_user_id and data.get("activo") == False:
            raise ConflictError('No puede desactivar su propia cuenta')

        if user_id == current_user_id and changes_role:
            raise ConflictError('No puede cambiar el rol de su propia cuenta')
        
        # Verificar que quede al menos un admin si se desactiva un admin
        should_check_last_admin = user.rol.nombre == "ADMIN" and (
            data.get("activo") == False
            or changes_role
        )
        if should_check_last_admin:
            admin_count = Usuario.query.join(RolUsuario).filter(
                RolUsuario.nombre == "ADMIN",
                Usuario.activo == True
            ).count()
            if admin_count <= 1:
                raise ConflictError('Debe quedar al menos un administrador en el sistema')
        
        # Actualizar campos permitidos
        if requested_rol is not None:
            user.id_rol = requested_rol.id
        
        if "nombre_usuario" in data:
            nombre_usuario = (data["nombre_usuario"] or "").strip()
            if not nombre_usuario:
                raise ValidationError('El nombre de usuario es obligatorio', details={"fields": {'nombre_usuario': 'El nombre de usuario es obligatorio'}})

            existing = Usuario.query.filter(
                Usuario.nombre_usuario == nombre_usuario,
                Usuario.id != user_id
            ).first()
            if existing:
                raise ConflictError('El nombre de usuario ya está en uso. Ingrese otro.', details={"fields": {'nombre_usuario': 'El nombre de usuario ya está en uso. Ingrese otro.'}})

            user.nombre_usuario = nombre_usuario

        if "mail" in data:
            mail = (data["mail"] or "").strip()
            if not mail:
                raise ValidationError('Ingrese el correo electrónico e intente nuevamente.', details={"fields": {'mail': 'Ingrese el correo electrónico.'}})

            # Verificar que el mail no exista
            existing = Usuario.query.filter(
                Usuario.mail == mail,
                Usuario.id != user_id
            ).first()
            if existing:
                raise ConflictError('El correo electrónico ya está en uso. Ingrese otro.', details={"fields": {'mail': 'El correo electrónico ya está en uso. Ingrese otro.'}})
            user.mail = mail
        
        if "activo" in data:
            user.activo = data["activo"]
        
        try:
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            raise Exception("Error al actualizar usuario")

    @staticmethod
    def get_rol_by_name(nombre: str):
        """Obtener un rol por nombre"""
        return RolUsuario.query.filter_by(nombre=nombre).first()

    @staticmethod
    def get_rol_by_id(rol_id: int):
        """Obtener un rol por ID"""
        return db.session.get(RolUsuario, rol_id)
