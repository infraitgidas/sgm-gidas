from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError as ValueError
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.controllers.pagination import paginate_query


def crear_fuente_financiamiento(data, user_id=None):
    if not data:
        raise ValueError("Los datos no pueden estar vacíos.")

    nombre_original = data.get("nombre")
    if not nombre_original or not isinstance(nombre_original, str):
        raise ValueError("El nombre debe ser un texto no vacío.")

    nombre_original = nombre_original.strip()
    validar_nombre_descriptivo(nombre_original)
    if not nombre_original:
        raise ValueError("El nombre no puede estar vacío.")

    # Normalización SOLO para validar duplicados
    nombre_normalizado = nombre_original.lower()

    existe = FuenteFinanciamiento.query.filter(
        db.func.lower(FuenteFinanciamiento.nombre) == nombre_normalizado
    ).first()

    if existe:
        raise ConflictError("Ya existe una fuente de financiamiento con ese nombre.")

    # Se guarda el nombre tal como lo escribió el usuario
    nueva = FuenteFinanciamiento(nombre=nombre_original)
    CatalogoAuditoriaService.marcar_creacion(nueva, user_id)
    db.session.add(nueva)

    try:
        db.session.commit()
        return nueva
    except Exception:
        db.session.rollback()
        raise


def actualizar_fuente_financiamiento(id, data, user_id=None):
    fuente = FuenteFinanciamiento.query.get(id)
    if not fuente:
        raise NotFoundError("Fuente de financiamiento no encontrada.")

    if fuente.deleted_at is not None:
        raise ConflictError("No se puede editar una fuente de financiamiento inactiva.")

    nombre = data.get("nombre")
    if not nombre or not isinstance(nombre, str):
        raise ValueError("El nombre debe ser un texto no vacío.")

    nombre = nombre.strip().lower()
    validar_nombre_descriptivo(nombre)
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")

    duplicado = FuenteFinanciamiento.query.filter(
        FuenteFinanciamiento.nombre == nombre,
        FuenteFinanciamiento.id != id
    ).first()

    if duplicado:
        raise ConflictError("Ya existe una fuente de financiamiento con ese nombre.")

    cambios = CatalogoAuditoriaService.construir_cambios(
        fuente,
        {"nombre": nombre}
    )
    fuente.nombre = nombre
    CatalogoAuditoriaService.marcar_actualizacion(fuente, cambios, user_id)

    try:
        db.session.commit()
        return fuente
    except Exception:
        db.session.rollback()
        raise


def eliminar_fuente_financiamiento(id, user_id=None):
    fuente = FuenteFinanciamiento.query.get(id)
    if not fuente:
        raise NotFoundError("Fuente de financiamiento no encontrada.")

    if fuente.becas.count() > 0:
        raise ConflictError(
            "No se puede eliminar la fuente de financiamiento porque está asociada a becarios."
        )

    if fuente.proyectos_investigacion.count() > 0:
        raise ConflictError(
            "No se puede eliminar la fuente de financiamiento porque está asociada a proyectos."
        )

    CatalogoAuditoriaService.marcar_baja(fuente, user_id)
    try:
        db.session.commit()
        return fuente
    except Exception:
        db.session.rollback()
        raise


def _consulta_fuentes_financiamiento(activos="true", orden="asc"):
    query = FuenteFinanciamiento.query
    if activos == "true":
        query = query.filter(FuenteFinanciamiento.deleted_at.is_(None))
    elif activos == "false":
        query = query.filter(FuenteFinanciamiento.deleted_at.isnot(None))
    sentido = FuenteFinanciamiento.nombre.desc if orden == "desc" else FuenteFinanciamiento.nombre.asc
    desempate = FuenteFinanciamiento.id.desc if orden == "desc" else FuenteFinanciamiento.id.asc
    return query.order_by(sentido(), desempate())


def listar_fuentes_financiamiento(activos="true"):
    return _consulta_fuentes_financiamiento(activos).all()


def listar_fuentes_financiamiento_paginado(page, per_page, activos="true", orden="asc"):
    return paginate_query(_consulta_fuentes_financiamiento(activos, orden), page, per_page)


def obtener_fuente_financiamiento_por_id(id):
    fuente = FuenteFinanciamiento.query.get(id)
    if not fuente:
        raise NotFoundError("No se encontró una fuente de financiamiento con ese id.")
    return fuente
