import bcrypt
from modules.shared.models.audit_mixin import AuditMixin
from extension import db



class RolUsuario(db.Model):
    __tablename__ = 'rol'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    

    def serialize(self):
        return {
            "id": self.id,
            "nombre": self.nombre
        }

class Usuario(db.Model, AuditMixin):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    contrasena = db.Column(db.String(128), nullable=False)
    mail = db.Column(db.String(120), unique=True, nullable=False)
    nombre_usuario = db.Column(db.String(80), unique=True, nullable=False)
    primer_login = db.Column(db.Boolean, default=True, nullable=False)

    id_rol = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    id_persona = db.Column(
        db.Integer,
        db.ForeignKey('persona.id'),
        nullable=True,
        unique=True   
    )

    rol = db.relationship("RolUsuario")
    grupos_utn = db.relationship(
        "UsuarioGrupoUtn",
        foreign_keys="UsuarioGrupoUtn.usuario_id",
        back_populates="usuario",
    )
    refresh_sessions = db.relationship(
        "RefreshTokenSession",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="RefreshTokenSession.user_id",
    )
    persona = db.relationship(
        "Persona",
        back_populates="usuario",
        foreign_keys=[id_persona]
    )
    

    def set_password(self, password_plano):
        assert password_plano, "La contraseña no puede estar vacía"
        self.contrasena = bcrypt.hashpw(
            password_plano.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def verificar_password(self, password_plano):
        if not self.contrasena:
            return False
        return bcrypt.checkpw(
            password_plano.encode("utf-8"),
            self.contrasena.encode("utf-8")
        )

    def cambiar_password(self, password_actual: str, password_nueva: str):
        if not self.verificar_password(password_actual):
            raise Exception("La contraseña actual es incorrecta")
        self.set_password(password_nueva)

    def serialize(self):
        return {
            "id": self.id,
            "mail": self.mail,
            "nombre_usuario": self.nombre_usuario,
            "rol": self.rol.nombre if self.rol else None,
            "primer_login": self.primer_login,
            "activo": self.activo,
            "fecha_creacion": self.created_at.isoformat() if self.created_at else None,
            "persona": {
                "id": self.persona.id,
                "nombre_apellido": self.persona.nombre_apellido
            } if self.persona else None,
            "nombre_apellido": self.persona.nombre_apellido if self.persona else None
        }
