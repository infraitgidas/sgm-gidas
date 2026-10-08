from sqlalchemy import func

from extension import db
from modules.grupo.models.visita_grupo import TipoVisita
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoVisitaService:
    @staticmethod
    def _get_or_404(tipo_id: int):
        tipo = db.session.get(TipoVisita, tipo_id)
        if not tipo:
            raise NotFoundError("Tipo de visita no encontrado")
        return tipo

    @staticmethod
    def _validar_nombre(nombre, tipo_id=None):
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValidationError("El nombre es obligatorio")

        nombre = " ".join(nombre.strip().split())
        validar_nombre_descriptivo(nombre)
        query = TipoVisita.query.filter(func.lower(TipoVisita.nombre) == nombre.lower())
        if tipo_id is not None:
            query = query.filter(TipoVisita.id != tipo_id)
        if query.first():
            raise ConflictError("Ya existe un tipo de visita con ese nombre")
        return nombre

    @staticmethod
    def get_all(activos="true"):
        return [item.serialize() for item in TipoVisitaService._query(activos).all()]

    @staticmethod
    def _query(activos="true", orden="asc"):
        query = TipoVisita.query
        if activos == "true":
            query = query.filter(TipoVisita.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(TipoVisita.deleted_at.isnot(None))
        nombre = TipoVisita.nombre.desc() if orden == "desc" else TipoVisita.nombre.asc()
        id_ = TipoVisita.id.desc() if orden == "desc" else TipoVisita.id.asc()
        return query.order_by(nombre, id_)

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        query = TipoVisitaService._query(activos, orden)
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [item.serialize() for item in rows], total

    @staticmethod
    def create(data, user_id=None):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")
        tipo = TipoVisita(nombre=TipoVisitaService._validar_nombre(data.get("nombre")))
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
        tipo = TipoVisitaService._get_or_404(tipo_id)
        if tipo.deleted_at is not None:
            raise ConflictError("No se puede editar un tipo de visita inactivo")
        if "nombre" in data:
            nombre = TipoVisitaService._validar_nombre(data["nombre"], tipo_id)
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
        tipo = TipoVisitaService._get_or_404(tipo_id)
        if tipo.visitas:
            raise ConflictError(
                "No se puede eliminar el tipo de visita porque tiene visitas asociadas"
            )
        CatalogoAuditoriaService.marcar_baja(tipo, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return {"message": "Eliminado correctamente"}
