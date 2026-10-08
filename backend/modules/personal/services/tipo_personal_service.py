from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from extension import db
from modules.personal.models.tipo_personal import TipoPersonal
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError


def crear_tipo_personal(data, user_id=None):
    if not data:
        raise ValidationError("Los datos no pueden estar vacíos.")

    nombre = data.get('nombre')
    if not nombre or not isinstance(nombre, str):
        raise ValidationError("El nombre debe ser un texto no vacío.")

    nombre = nombre.strip()
    validar_nombre_descriptivo(nombre)
    if not nombre:
        raise ValidationError("El nombre no puede estar vacío.")

    if TipoPersonal.query.filter_by(nombre=nombre).first():
        raise ConflictError("Ya existe un tipo de personal con ese nombre.")

    nuevo_tipo = TipoPersonal(nombre=nombre)
    CatalogoAuditoriaService.marcar_creacion(nuevo_tipo, user_id)
    db.session.add(nuevo_tipo)

    try:
        db.session.commit()
        return nuevo_tipo
    except Exception:
        db.session.rollback()
        raise


def actualizar_tipo_personal(id, data, user_id=None):
    tipo_personal = TipoPersonal.query.get(id)
    if not tipo_personal:
        raise NotFoundError("Tipo de personal no encontrado.")

    nombre = data.get('nombre')
    if not nombre or not isinstance(nombre, str):
        raise ValidationError("El nombre debe ser un texto no vacío.")

    nombre = nombre.strip()
    validar_nombre_descriptivo(nombre)
    if not nombre:
        raise ValidationError("El nombre no puede estar vacío.")

    if tipo_personal.deleted_at is not None:
        raise ConflictError("No se puede editar un tipo de personal inactivo.")

    duplicado = TipoPersonal.query.filter(
        TipoPersonal.nombre == nombre,
        TipoPersonal.id != id
    ).first()

    if duplicado:
        raise ConflictError("Ya existe un tipo de personal con ese nombre.")

    cambios = CatalogoAuditoriaService.construir_cambios(
        tipo_personal,
        {"nombre": nombre}
    )
    tipo_personal.nombre = nombre
    CatalogoAuditoriaService.marcar_actualizacion(tipo_personal, cambios, user_id)

    try:
        db.session.commit()
        return tipo_personal
    except Exception:
        db.session.rollback()
        raise


def eliminar_tipo_personal(id, user_id=None):
    tipo_personal = TipoPersonal.query.get(id)
    if not tipo_personal:
        raise NotFoundError("Tipo de personal no encontrado.")

    if tipo_personal.personal.count() > 0:
        raise ConflictError(
            "No se puede eliminar el tipo de personal porque está asociado a personal."
        )

    CatalogoAuditoriaService.marcar_baja(tipo_personal, user_id)

    try:
        db.session.commit()
        return tipo_personal
    except Exception:
        db.session.rollback()
        raise


def _consulta_tipos(activos="true", orden="asc"):
    query = TipoPersonal.query
    if activos == "true":
        query = query.filter(TipoPersonal.deleted_at.is_(None), TipoPersonal.activo.is_(True))
    elif activos == "false":
        query = query.filter(TipoPersonal.deleted_at.isnot(None))
    nombre = TipoPersonal.nombre.desc() if orden == "desc" else TipoPersonal.nombre.asc()
    id_ = TipoPersonal.id.desc() if orden == "desc" else TipoPersonal.id.asc()
    return query.order_by(nombre, id_)


def listar_tipos(activos="true"):
    return _consulta_tipos(activos).all()


def listar_tipos_paginado(page, per_page, activos="true", orden="asc"):
    query = _consulta_tipos(activos, orden)
    return query.offset((page - 1) * per_page).limit(per_page).all(), query.count()


def obtener_tipo_por_id(id):
    tipo = TipoPersonal.query.get(id)
    if not tipo:
        raise NotFoundError("No se encontró un tipo con ese id")
    return tipo
