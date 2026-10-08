from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from modules.produccion.models.actividad_docencia import RolActividad
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from extension import db
from sqlalchemy import func
from modules.shared.services.catalog_pagination import catalog_page


class RolActividadService:

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        return catalog_page(RolActividad, RolActividad.nombre, activos=activos, orden=orden, page=page, per_page=per_page)

    @staticmethod
    def _validar_id(rol_id: int):
        if isinstance(rol_id, bool) or not isinstance(rol_id, int) or rol_id <= 0:
            raise ValidationError("El id debe ser un entero positivo")
        return rol_id

    @staticmethod
    def _validar_payload(data: dict):
        if data is None or not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")
        return data

    @staticmethod
    def _validar_nombre(nombre: str, rol_id: int = None):
        if nombre is None:
            raise ValidationError("El nombre es obligatorio")

        if not isinstance(nombre, str):
            raise ValidationError("El nombre debe ser texto")

        nombre = nombre.strip()
        validar_nombre_descriptivo(nombre)
        if not nombre:
            raise ValidationError("El nombre no puede estar vacio")

        if len(nombre) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")

        query = RolActividad.query.filter(
            func.lower(RolActividad.nombre) == nombre.lower()
        )

        if rol_id is not None:
            query = query.filter(RolActividad.id != rol_id)

        if query.first():
            raise ConflictError("Ya existe un rol de actividad con ese nombre")

        return nombre

    @staticmethod
    def _get_or_404(rol_id: int):
        rol = RolActividad.query.get(RolActividadService._validar_id(rol_id))
        if not rol:
            raise NotFoundError("Rol de Actividad no encontrado")
        return rol

    @staticmethod
    def get_all(activos="true"):
        query = RolActividad.query
        if activos == "true":
            query = query.filter(RolActividad.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(RolActividad.deleted_at.isnot(None))
        return [
            r.serialize()
            for r in query.order_by(RolActividad.nombre.asc()).all()
        ]

    @staticmethod
    def get_by_id(rol_id: int):
        rol = RolActividadService._get_or_404(rol_id)
        return rol.serialize()

    @staticmethod
    def create(data: dict, user_id=None):
        RolActividadService._validar_payload(data)
        nombre = RolActividadService._validar_nombre(data.get("nombre"))

        rol = RolActividad(nombre=nombre)
        CatalogoAuditoriaService.marcar_creacion(rol, user_id)
        db.session.add(rol)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return rol.serialize()

    @staticmethod
    def update(rol_id: int, data: dict, user_id=None):
        RolActividadService._validar_payload(data)
        rol = RolActividadService._get_or_404(rol_id)

        if rol.deleted_at is not None:
            raise ConflictError("No se puede editar un rol de actividad inactivo")

        if "nombre" in data:
            nombre = RolActividadService._validar_nombre(
                data.get("nombre"),
                rol_id=rol.id
            )
            cambios = CatalogoAuditoriaService.construir_cambios(
                rol,
                {"nombre": nombre}
            )
            rol.nombre = nombre
            CatalogoAuditoriaService.marcar_actualizacion(rol, cambios, user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return rol.serialize()

    @staticmethod
    def delete(rol_id: int, user_id=None):
        rol = RolActividadService._get_or_404(rol_id)

        if rol.actividades_docencia:
            raise ConflictError(
                "No se puede eliminar el rol de actividad porque tiene actividades asociadas"
            )

        CatalogoAuditoriaService.marcar_baja(rol, user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Eliminado correctamente"}
