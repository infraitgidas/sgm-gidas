from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from sqlalchemy import func

from modules.proyectos.models.proyecto_investigacion import TipoProyecto
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from extension import db
from modules.shared.services.catalog_pagination import catalog_page


class TipoProyectoService:

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        return catalog_page(TipoProyecto, TipoProyecto.nombre, activos=activos, orden=orden, page=page, per_page=per_page)

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
            raise ValidationError("El nombre del tipo de proyecto es obligatorio")

        if not isinstance(nombre, str):
            raise ValidationError("El nombre debe ser texto")

        nombre = " ".join(nombre.strip().split())
        validar_nombre_descriptivo(nombre)
        if not nombre:
            raise ValidationError("El nombre del tipo de proyecto es obligatorio")

        if len(nombre) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")

        existente = TipoProyecto.query.filter(
            func.lower(TipoProyecto.nombre) == nombre.lower()
        )

        if tipo_id is not None:
            existente = existente.filter(TipoProyecto.id != tipo_id)

        if existente.first():
            raise ConflictError("Ya existe un tipo de proyecto con ese nombre")

        return nombre

    @staticmethod
    def _obtener_tipo_o_error(tipo_id):
        tipo_id = TipoProyectoService._validar_id_positivo(tipo_id)
        tipo = TipoProyecto.query.get(tipo_id)
        if not tipo:
            raise NotFoundError("Tipo de proyecto no encontrado")
        return tipo

    @staticmethod
    def _serializar(tipo):
        return tipo.serialize()

    @staticmethod
    def get_all(activos="true"):
        query = TipoProyecto.query
        if activos == "true":
            query = query.filter(TipoProyecto.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(TipoProyecto.deleted_at.isnot(None))
        tipos = query.order_by(TipoProyecto.nombre.asc()).all()
        return [TipoProyectoService._serializar(t) for t in tipos]

    @staticmethod
    def get_by_id(tipo_id: int):
        tipo = TipoProyectoService._obtener_tipo_o_error(tipo_id)
        return TipoProyectoService._serializar(tipo)

    @staticmethod
    def create(data: dict, user_id=None):
        data = TipoProyectoService._validar_data(data)
        nombre = TipoProyectoService._validar_nombre(data.get("nombre"))

        tipo = TipoProyecto(nombre=nombre)
        CatalogoAuditoriaService.marcar_creacion(tipo, user_id)

        db.session.add(tipo)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return TipoProyectoService._serializar(tipo)

    @staticmethod
    def update(tipo_id: int, data: dict, user_id=None):
        data = TipoProyectoService._validar_data(data)
        tipo = TipoProyectoService._obtener_tipo_o_error(tipo_id)
        if tipo.deleted_at is not None:
            raise ConflictError("No se puede editar un tipo de proyecto inactivo")

        nombre = TipoProyectoService._validar_nombre(data.get("nombre"), tipo.id)
        cambios = CatalogoAuditoriaService.construir_cambios(tipo, {"nombre": nombre})
        tipo.nombre = nombre
        CatalogoAuditoriaService.marcar_actualizacion(tipo, cambios, user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return TipoProyectoService._serializar(tipo)

    @staticmethod
    def delete(tipo_id: int, user_id=None):
        tipo = TipoProyectoService._obtener_tipo_o_error(tipo_id)

        if len(tipo.proyectos_investigacion) > 0:
            raise ConflictError(
                "No se puede eliminar el tipo porque tiene proyectos asociados"
            )

        CatalogoAuditoriaService.marcar_baja(tipo, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Tipo de proyecto eliminado correctamente"}
