from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from modules.transferencia.models.transferencia_socio import TipoContrato
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from extension import db
from sqlalchemy import func
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError as ValueError


class TipoContratoService:

    # -------------------------------------------------
    # Validadores
    # -------------------------------------------------

    @staticmethod
    def _validar_id(tipo_contrato_id):
        if (
            isinstance(tipo_contrato_id, bool)
            or not isinstance(tipo_contrato_id, int)
            or tipo_contrato_id <= 0
        ):
            raise ValueError("El id debe ser un entero positivo")
        return tipo_contrato_id

    @staticmethod
    def _validar_payload(data):
        if data is None or not isinstance(data, dict) or not data:
            raise ValueError("Los datos no pueden estar vacios")
        return data

    @staticmethod
    def _validar_nombre(nombre, contrato_id=None):
        if nombre is None:
            raise ValueError("El nombre es obligatorio")

        if not isinstance(nombre, str):
            raise ValueError("El nombre debe ser texto")

        nombre = nombre.strip()
        validar_nombre_descriptivo(nombre)

        if not nombre:
            raise ValueError("El nombre no puede estar vacio")

        if len(nombre) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")

        query = TipoContrato.query.filter(
            func.lower(TipoContrato.nombre) == nombre.lower()
        )

        if contrato_id is not None:
            query = query.filter(TipoContrato.id != contrato_id)

        if query.first():
            raise ConflictError("Ya existe un tipo de contrato con ese nombre")

        return nombre

    @staticmethod
    def _get_or_404(tipo_contrato_id):
        tipo = TipoContrato.query.get(TipoContratoService._validar_id(tipo_contrato_id))
        if not tipo:
            raise NotFoundError("Tipo de contrato no encontrado")
        return tipo

    # -------------------------------------------------
    # CRUD
    # -------------------------------------------------

    @staticmethod
    def _list_query(activos="true", orden="asc"):
        query = TipoContrato.query
        if activos == "true":
            query = query.filter(TipoContrato.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(TipoContrato.deleted_at.isnot(None))
        nombre = TipoContrato.nombre.desc() if orden == "desc" else TipoContrato.nombre.asc()
        id_ = TipoContrato.id.desc() if orden == "desc" else TipoContrato.id.asc()
        return query.order_by(nombre, id_)

    @staticmethod
    def get_all(activos="true"):
        return [t.serialize() for t in TipoContratoService._list_query(activos).all()]

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        query = TipoContratoService._list_query(activos, orden)
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [t.serialize() for t in rows], total

    @staticmethod
    def get_by_id(tipo_contrato_id):
        tipo = TipoContratoService._get_or_404(tipo_contrato_id)
        return tipo.serialize()

    @staticmethod
    def create(data: dict, user_id=None):
        TipoContratoService._validar_payload(data)
        nombre = TipoContratoService._validar_nombre(data.get("nombre"))

        tipo = TipoContrato(nombre=nombre)
        CatalogoAuditoriaService.marcar_creacion(tipo, user_id)

        db.session.add(tipo)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return tipo.serialize()

    @staticmethod
    def update(tipo_contrato_id, data: dict, user_id=None):
        TipoContratoService._validar_payload(data)
        tipo = TipoContratoService._get_or_404(tipo_contrato_id)

        if tipo.deleted_at is not None:
            raise ConflictError("No se puede editar un tipo de contrato inactivo")

        if "nombre" in data:
            nombre = TipoContratoService._validar_nombre(
                data["nombre"],
                contrato_id=tipo.id
            )
            cambios = CatalogoAuditoriaService.construir_cambios(
                tipo,
                {"nombre": nombre}
            )
            tipo.nombre = nombre
            CatalogoAuditoriaService.marcar_actualizacion(tipo, cambios, user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return tipo.serialize()

    @staticmethod
    def delete(tipo_contrato_id, user_id=None):
        tipo = TipoContratoService._get_or_404(tipo_contrato_id)

        if any(t.deleted_at is None for t in tipo.transferencias):
            raise ConflictError(
                "No se puede eliminar el tipo de contrato porque tiene transferencias asociadas"
            )

        CatalogoAuditoriaService.marcar_baja(tipo, user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Tipo de contrato eliminado correctamente"}
