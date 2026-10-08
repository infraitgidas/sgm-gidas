from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from sqlalchemy import func

from modules.recursos.models.erogacion import TipoErogacion
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.services.catalog_pagination import catalog_page
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError


class TipoErogacionService:

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        return catalog_page(TipoErogacion, TipoErogacion.nombre, activos=activos, orden=orden, page=page, per_page=per_page)

    @staticmethod
    def _validar_id_positivo(tipo_id):
        if isinstance(tipo_id, bool) or not isinstance(tipo_id, int):
            raise ValidationError("El id debe ser un entero positivo")

        if tipo_id <= 0:
            raise ValidationError("El id debe ser un entero positivo")

        return tipo_id

    @staticmethod
    def _validar_data(data):
        if data is None:
            raise ValidationError("Los datos no pueden estar vacíos")

        if not isinstance(data, dict):
            raise ValidationError("Los datos deben enviarse en un objeto válido")

        if not data:
            raise ValidationError("Los datos no pueden estar vacíos")

        return data

    @staticmethod
    def _validar_nombre(nombre, tipo_id=None):
        if nombre is None:
            raise ValidationError("El nombre es obligatorio")

        if not isinstance(nombre, str):
            raise ValidationError("El nombre debe ser texto")

        nombre = nombre.strip()
        validar_nombre_descriptivo(nombre)
        if not nombre:
            raise ValidationError("El nombre no puede estar vacío")

        if len(nombre) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")

        existe = TipoErogacion.query.filter(
            func.lower(TipoErogacion.nombre) == nombre.lower()
        )

        if tipo_id is not None:
            existe = existe.filter(TipoErogacion.id != tipo_id)

        if existe.first():
            raise ConflictError("Ya existe un tipo de erogación con ese nombre")

        return nombre

    @staticmethod
    def _obtener_tipo_o_error(tipo_id):
        tipo_id = TipoErogacionService._validar_id_positivo(tipo_id)
        tipo = TipoErogacion.query.get(tipo_id)
        if not tipo:
            raise NotFoundError("Tipo de erogación no encontrado")
        return tipo

    @staticmethod
    def get_all(activos="true"):
        query = TipoErogacion.query
        if activos == "true":
            query = query.filter(TipoErogacion.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(TipoErogacion.deleted_at.isnot(None))
        return [t.serialize() for t in query.order_by(TipoErogacion.nombre.asc()).all()]

    @staticmethod
    def get_by_id(tipo_id: int):
        tipo = TipoErogacionService._obtener_tipo_o_error(tipo_id)
        return tipo.serialize()

    @staticmethod
    def create(data: dict, user_id=None):
        data = TipoErogacionService._validar_data(data)
        nombre = TipoErogacionService._validar_nombre(data.get("nombre"))

        nuevo = TipoErogacion(nombre=nombre)
        CatalogoAuditoriaService.marcar_creacion(nuevo, user_id)

        db.session.add(nuevo)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return nuevo.serialize()

    @staticmethod
    def update(tipo_id: int, data: dict, user_id=None):
        data = TipoErogacionService._validar_data(data)
        tipo = TipoErogacionService._obtener_tipo_o_error(tipo_id)
        if tipo.deleted_at is not None:
            raise ConflictError("No se puede editar un tipo de erogacion inactivo")

        nombre = TipoErogacionService._validar_nombre(data.get("nombre"), tipo.id)
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
    def delete(tipo_id: int, user_id=None):
        tipo = TipoErogacionService._obtener_tipo_o_error(tipo_id)

        if len(tipo.erogaciones) > 0:
            raise ConflictError(
                "No se puede eliminar el tipo de erogación porque está asociado a erogaciones"
            )

        CatalogoAuditoriaService.marcar_baja(tipo, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Tipo de erogación eliminado correctamente"}
