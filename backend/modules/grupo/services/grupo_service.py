from extension import db
from modules.shared.services.text_validation import has_letter
from modules.shared.exceptions import ValidationError as ValueError
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
from modules.shared.exceptions import NotFoundError
from modules.shared.services.auditoria_service import AuditoriaService


ETIQUETAS_GRUPO = {
    "nombre_unidad_academica": "la facultad regional",
    "nombre_sigla_grupo": "el nombre y sigla del grupo",
    "mail": "el correo electrónico",
    "objetivo_desarrollo": "los objetivos del grupo",
}


def crear_grupo_utn(data, user_id):
    if GrupoInvestigacionUtn.query.filter(
        GrupoInvestigacionUtn.deleted_at.is_(None)
    ).first():
        raise ValueError("Ya existe un grupo de investigación activo.")

    if not data:
        raise ValueError("Los datos no pueden estar vacíos.")

    campos = [
        "nombre_unidad_academica",
        "nombre_sigla_grupo",
        "mail",
        "objetivo_desarrollo"
    ]

    for campo in campos:
        if not data.get(campo):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {ETIQUETAS_GRUPO[campo]}."}})
        if campo in {"nombre_unidad_academica", "nombre_sigla_grupo"} and not has_letter(data[campo]):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"{ETIQUETAS_GRUPO[campo].capitalize()} debe contener letras."}})

    nuevo_grupo = GrupoInvestigacionUtn(
        nombre_unidad_academica=data["nombre_unidad_academica"].strip(),
        nombre_sigla_grupo=data["nombre_sigla_grupo"].strip(),
        mail=data["mail"].strip(),
        objetivo_desarrollo=data["objetivo_desarrollo"].strip(),
        created_by=user_id
    )

    db.session.add(nuevo_grupo)
    db.session.flush()
    db.session.add(UsuarioGrupoUtn(
        usuario_id=user_id,
        grupo_utn_id=nuevo_grupo.id,
        created_by=user_id,
    ))
    db.session.commit()

    return nuevo_grupo


def obtener_grupo_utn():
    return GrupoInvestigacionUtn.query.filter(
        GrupoInvestigacionUtn.deleted_at.is_(None)
    ).first()


def listar_grupos_utn_activos(page=None, per_page=None, orden="asc"):
    query = GrupoInvestigacionUtn.query.filter(
        GrupoInvestigacionUtn.deleted_at.is_(None)
    )
    total = query.count() if page is not None else None
    name_order = (GrupoInvestigacionUtn.nombre_sigla_grupo.desc() if orden == "desc"
                  else GrupoInvestigacionUtn.nombre_sigla_grupo.asc())
    query = query.order_by(name_order, GrupoInvestigacionUtn.id.asc())
    if page is not None:
        query = query.offset((page - 1) * per_page).limit(per_page)
    data = [
        {"id": grupo.id, "nombre": grupo.nombre_sigla_grupo}
        for grupo in query.all()
    ]
    return (data, total) if page is not None else data


def obtener_historial_grupo_utn(grupo_id):
    grupo = GrupoInvestigacionUtn.query.filter(
        GrupoInvestigacionUtn.id == grupo_id,
        GrupoInvestigacionUtn.deleted_at.is_(None),
    ).first()
    if not grupo:
        raise NotFoundError("Historial no encontrado")
    return AuditoriaService.obtener_historial_entidad("grupo_utn", grupo.id)


def actualizar_grupo_utn(data, user_id):
    grupo = obtener_grupo_utn()
    if not grupo:
        raise ValueError("No existe grupo activo.")

    if not data:
        raise ValueError("Los datos no pueden estar vacíos.")

    cambios = {}
    for campo in [
        "mail",
        "nombre_unidad_academica",
        "objetivo_desarrollo",
        "nombre_sigla_grupo"
    ]:
        if campo in data:
            valor = data[campo]
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {ETIQUETAS_GRUPO[campo]}."}})
            if campo in {"nombre_unidad_academica", "nombre_sigla_grupo"} and not has_letter(valor):
                raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"{ETIQUETAS_GRUPO[campo].capitalize()} debe contener letras."}})
            nuevo_valor = valor.strip()
            cambio = AuditoriaService.construir_cambio(getattr(grupo, campo), nuevo_valor)
            if cambio:
                cambios[campo] = cambio
                setattr(grupo, campo, nuevo_valor)

    if cambios:
        grupo.mark_updated(user_id)
        AuditoriaService.registrar_cambios(
            entidad="grupo_utn",
            registro_id=grupo.id,
            cambios=cambios,
            user_id=user_id,
        )
    db.session.commit()
    return grupo


def eliminar_grupo_utn(user_id):
    grupo = obtener_grupo_utn()

    if not grupo:
        raise ValueError("No hay grupo activo para eliminar.")

    grupo.soft_delete(user_id)

    db.session.commit()

    return {"message": "Grupo eliminado correctamente (soft delete)."}

def restaurar_grupo_utn():
    grupo = db.session.query(GrupoInvestigacionUtn).filter(
        GrupoInvestigacionUtn.deleted_at.isnot(None)
    ).first()

    if not grupo:
        raise ValueError("No existe grupo eliminado para restaurar.")

    grupo.restore()

    db.session.commit()

    return grupo
