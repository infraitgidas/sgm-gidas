from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from sqlalchemy import func

from extension import db
from modules.personal.models.personal import TipoDedicacion
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError


def _validar_id_positivo(tipo_dedicacion_id):
    if isinstance(tipo_dedicacion_id, bool) or not isinstance(tipo_dedicacion_id, int):
        raise ValidationError("El id debe ser un entero positivo.")

    if tipo_dedicacion_id <= 0:
        raise ValidationError("El id debe ser un entero positivo.")

    return tipo_dedicacion_id


def _validar_data(data):
    if data is None:
        raise ValidationError("Los datos no pueden estar vacíos.")

    if not isinstance(data, dict):
        raise ValidationError("Los datos deben enviarse en un objeto válido.")

    if not data:
        raise ValidationError("Los datos no pueden estar vacíos.")

    return data


def _validar_nombre(nombre, tipo_dedicacion_id=None):
    if nombre is None:
        raise ValidationError("El nombre es obligatorio.")

    if not isinstance(nombre, str):
        raise ValidationError("El nombre debe ser un texto no vacío.")

    nombre = nombre.strip()
    validar_nombre_descriptivo(nombre)
    if not nombre:
        raise ValidationError("El nombre no puede estar vacío.")

    if len(nombre) < 2:
        raise ValidationError("El nombre debe tener al menos 2 caracteres.")

    query = TipoDedicacion.query.filter(
        func.lower(TipoDedicacion.nombre) == nombre.lower()
    )

    if tipo_dedicacion_id is not None:
        query = query.filter(TipoDedicacion.id != tipo_dedicacion_id)

    if query.first():
        raise ConflictError("Ya existe un tipo de dedicación con ese nombre.")

    return nombre


def _obtener_tipo_dedicacion_o_error(tipo_dedicacion_id):
    tipo_dedicacion_id = _validar_id_positivo(tipo_dedicacion_id)
    tipo = TipoDedicacion.query.get(tipo_dedicacion_id)

    if not tipo:
        raise NotFoundError("Tipo de dedicación no encontrado.")

    return tipo


def crear_tipo_dedicacion(data, user_id=None):
    data = _validar_data(data)
    nombre = _validar_nombre(data.get("nombre"))

    nuevo = TipoDedicacion(nombre=nombre)
    CatalogoAuditoriaService.marcar_creacion(nuevo, user_id)
    db.session.add(nuevo)

    try:
        db.session.commit()
        return nuevo
    except Exception:
        db.session.rollback()
        raise


def actualizar_tipo_dedicacion(id, data, user_id=None):
    data = _validar_data(data)
    tipo = _obtener_tipo_dedicacion_o_error(id)
    if tipo.deleted_at is not None:
        raise ConflictError("No se puede editar un tipo de dedicacion inactivo.")

    nombre = _validar_nombre(data.get("nombre"), tipo_dedicacion_id=tipo.id)

    cambios = CatalogoAuditoriaService.construir_cambios(tipo, {"nombre": nombre})
    tipo.nombre = nombre
    CatalogoAuditoriaService.marcar_actualizacion(tipo, cambios, user_id)

    try:
        db.session.commit()
        return tipo
    except Exception:
        db.session.rollback()
        raise


def eliminar_tipo_dedicacion(id, user_id=None):
    tipo = _obtener_tipo_dedicacion_o_error(id)

    if len(tipo.investigadores) > 0:
        raise ConflictError(
            "No se puede eliminar el tipo de dedicación porque está asociado a investigadores."
        )

    CatalogoAuditoriaService.marcar_baja(tipo, user_id)
    try:
        db.session.commit()
        return tipo
    except Exception:
        db.session.rollback()
        raise


def _consulta_tipos_dedicacion(activos="true", orden="asc"):
    query = TipoDedicacion.query
    if activos == "true":
        query = query.filter(TipoDedicacion.deleted_at.is_(None))
    elif activos == "false":
        query = query.filter(TipoDedicacion.deleted_at.isnot(None))
    nombre = TipoDedicacion.nombre.desc() if orden == "desc" else TipoDedicacion.nombre.asc()
    id_ = TipoDedicacion.id.desc() if orden == "desc" else TipoDedicacion.id.asc()
    return query.order_by(nombre, id_)


def listar_tipos_dedicacion(activos="true"):
    return _consulta_tipos_dedicacion(activos).all()


def listar_tipos_dedicacion_paginado(page, per_page, activos="true", orden="asc"):
    query = _consulta_tipos_dedicacion(activos, orden)
    return query.offset((page - 1) * per_page).limit(per_page).all(), query.count()



def obtener_tipo_dedicacion_por_id(id):
    return _obtener_tipo_dedicacion_o_error(id)
