from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from sqlalchemy import func

from extension import db
from modules.produccion.models.trabajo_reunion import TipoReunion
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.services.catalog_pagination import catalog_page


class TipoReunionService:

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        return catalog_page(TipoReunion, TipoReunion.nombre, activos=activos, orden=orden, page=page, per_page=per_page)

    @staticmethod
    def _get_or_404(tipo_id: int):
        tipo = db.session.get(TipoReunion, tipo_id)
        if not tipo:
            raise NotFoundError("Tipo de reunion no encontrado")
        return tipo

    @staticmethod
    def _validar_nombre(nombre, tipo_id=None):
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValidationError("El nombre es obligatorio")
        nombre = " ".join(nombre.strip().split())
        validar_nombre_descriptivo(nombre)
        query = TipoReunion.query.filter(func.lower(TipoReunion.nombre) == nombre.lower())
        if tipo_id is not None:
            query = query.filter(TipoReunion.id != tipo_id)
        if query.first():
            raise ConflictError("Ya existe un tipo de reunion con ese nombre")
        return nombre

    @staticmethod
    def get_all(activos="true"):
        query = TipoReunion.query
        if activos == "true":
            query = query.filter(TipoReunion.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(TipoReunion.deleted_at.isnot(None))
        return [item.serialize() for item in query.order_by(TipoReunion.nombre.asc()).all()]

    @staticmethod
    def create(data, user_id=None):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")
        tipo = TipoReunion(nombre=TipoReunionService._validar_nombre(data.get("nombre")))
        CatalogoAuditoriaService.marcar_creacion(tipo, user_id)
        db.session.add(tipo)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return tipo.serialize()

    @staticmethod
    def update(tipo_id, data, user_id=None):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")
        tipo = TipoReunionService._get_or_404(tipo_id)
        if tipo.deleted_at is not None:
            raise ConflictError("No se puede editar un tipo de reunion inactivo")
        if "nombre" in data:
            nombre = TipoReunionService._validar_nombre(data["nombre"], tipo_id)
            cambios = CatalogoAuditoriaService.construir_cambios(tipo, {"nombre": nombre})
            tipo.nombre = nombre
            CatalogoAuditoriaService.marcar_actualizacion(tipo, cambios, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return tipo.serialize()

    @staticmethod
    def delete(tipo_id, user_id=None):
        tipo = TipoReunionService._get_or_404(tipo_id)
        relaciones = (
            getattr(tipo, "trabajos_reunion_cientifica", None),
            getattr(tipo, "visitas", None),
        )
        if any(relacion for relacion in relaciones):
            raise ConflictError("No se puede eliminar el tipo de reunion porque tiene trabajos asociados")
        CatalogoAuditoriaService.marcar_baja(tipo, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return {"message": "Eliminado correctamente"}
