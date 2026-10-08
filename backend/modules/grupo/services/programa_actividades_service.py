from extension import db
from modules.shared.exceptions import ValidationError as ValueError
from modules.grupo.models.programa_actividades import PlanificacionGrupo
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService


def _validar_user_id(user_id):
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("No pudimos procesar la solicitud. Intente nuevamente.")


def _validar_descripcion(descripcion):
    if not isinstance(descripcion, str):
        raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"descripcion": "Ingrese la descripción de la planificación."}})

    descripcion = " ".join(descripcion.strip().split())
    if not descripcion:
        raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"descripcion": "Ingrese la descripción de la planificación."}})

    return descripcion


def _validar_anio(anio):
    if not isinstance(anio, int) or anio < 2000:
        raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"anio": "Ingrese un año válido desde 2000."}})

    return anio


def _obtener_grupo_activo(grupo_id):
    if not isinstance(grupo_id, int) or grupo_id <= 0:
        raise ValueError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

    grupo = db.session.get(GrupoInvestigacionUtn, grupo_id)
    if not grupo or grupo.deleted_at is not None:
        raise ValueError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

    return grupo


def _validar_planificacion_unica(grupo_id, anio, planificacion_id=None):
    query = PlanificacionGrupo.query.filter(
        PlanificacionGrupo.grupo_id == grupo_id,
        PlanificacionGrupo.anio == anio,
        PlanificacionGrupo.deleted_at.is_(None)
    )

    if planificacion_id is not None:
        query = query.filter(PlanificacionGrupo.id != planificacion_id)

    if query.first():
        raise ValueError("Ya existe una planificación para ese año. Elija otro año e intente nuevamente.", details={"fields": {"anio": "Elija un año sin planificación existente."}})


def crear_planificacion_grupo(data, user_id):
    if not data:
        raise ValueError("Los datos no pueden estar vacios.")

    _validar_user_id(user_id)
    descripcion = _validar_descripcion(data.get("descripcion"))
    anio = _validar_anio(data.get("anio"))
    grupo = _obtener_grupo_activo(data.get("grupo_id"))
    _validar_planificacion_unica(grupo.id, anio)

    planificacion = PlanificacionGrupo(
        descripcion=descripcion,
        anio=anio,
        grupo_id=grupo.id,
        activo=True,
        created_by=user_id,
    )

    db.session.add(planificacion)
    try:
        db.session.commit()
        return planificacion
    except Exception:
        db.session.rollback()
        raise


def actualizar_planificacion_grupo(id, data, user_id):
    if not data:
        raise ValueError("Los datos no pueden estar vacios.")

    _validar_user_id(user_id)
    planificacion = db.session.get(PlanificacionGrupo, id)
    if not planificacion or planificacion.deleted_at is not None:
        raise ValueError("Planificacion no encontrada.")

    cambios = {}
    if "descripcion" in data:
        descripcion = _validar_descripcion(data["descripcion"])
        cambio = AuditoriaService.construir_cambio(planificacion.descripcion, descripcion)
        if cambio:
            cambios["descripcion"] = cambio
            planificacion.descripcion = descripcion

    nuevo_anio = planificacion.anio
    if "anio" in data:
        nuevo_anio = _validar_anio(data["anio"])

    nuevo_grupo_id = planificacion.grupo_id
    if "grupo_id" in data:
        nuevo_grupo_id = _obtener_grupo_activo(data["grupo_id"]).id

    if (
        nuevo_anio != planificacion.anio
        or nuevo_grupo_id != planificacion.grupo_id
    ):
        _validar_planificacion_unica(
            nuevo_grupo_id,
            nuevo_anio,
            planificacion_id=id
        )

    cambio_anio = AuditoriaService.construir_cambio(planificacion.anio, nuevo_anio)
    if cambio_anio:
        cambios["anio"] = cambio_anio
        planificacion.anio = nuevo_anio

    cambio_grupo = AuditoriaService.construir_cambio(planificacion.grupo_id, nuevo_grupo_id)
    if cambio_grupo:
        cambios["grupo_id"] = cambio_grupo
        planificacion.grupo_id = nuevo_grupo_id

    if cambios:
        planificacion.mark_updated(user_id)
        AuditoriaService.registrar_cambios(
            entidad="planificacion_grupo",
            registro_id=planificacion.id,
            cambios=cambios,
            user_id=user_id,
        )

    try:
        db.session.commit()
        return planificacion
    except Exception:
        db.session.rollback()
        raise


def eliminar_planificacion_grupo(id, user_id=None):
    _validar_user_id(user_id)

    planificacion = db.session.get(PlanificacionGrupo, id)
    if not planificacion or planificacion.deleted_at is not None:
        raise ValueError("Planificacion no encontrada.")

    planificacion.soft_delete(user_id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _consulta_planificaciones(activos="true", orden="asc"):
    query = PlanificacionGrupo.query

    if activos is None:
        activos = "true"

    activos = activos.strip().lower()

    if activos == "true":
        query = query.filter(PlanificacionGrupo.deleted_at.is_(None))
    elif activos == "false":
        query = query.filter(PlanificacionGrupo.deleted_at.isnot(None))
    elif activos == "all":
        pass
    else:
        query = query.filter(PlanificacionGrupo.deleted_at.is_(None))

    id_ = PlanificacionGrupo.id.desc() if orden == "desc" else PlanificacionGrupo.id.asc()
    return query.order_by(id_)


def listar_planificaciones(activos="true"):
    return _consulta_planificaciones(activos).all()


def listar_planificaciones_paginado(page, per_page, activos="true", orden="asc"):
    query = _consulta_planificaciones(activos, orden)
    total = query.count()
    return query.offset((page - 1) * per_page).limit(per_page).all(), total


def obtener_planificacion_por_id(id):
    planificacion = db.session.get(PlanificacionGrupo, id)
    if not planificacion or planificacion.deleted_at is not None:
        raise ValueError("Planificacion no encontrada.")
    return planificacion


def obtener_historial_planificacion(id):
    planificacion = db.session.get(PlanificacionGrupo, id)
    if not planificacion:
        raise ValueError("Planificacion no encontrada.")
    return AuditoriaService.obtener_historial_entidad(
        entidad="planificacion_grupo",
        registro_id=planificacion.id,
    )
