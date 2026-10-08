from sqlalchemy import false, func, literal, or_, union_all

from extension import db
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.personal.models.personal import Becario, Investigador, Personal, TipoDedicacion, TipoFormacion
from modules.personal.models.tipo_personal import TipoPersonal
from modules.shared.exceptions import NotFoundError, ValidationError


TIPOS_VALIDOS = {"personal", "ptaa", "profesional", "becario", "investigador"}
ACTIVOS_VALIDOS = {"true", "false", "all"}
ORDENES = {"nombre": "nombre_apellido", "clase": "rol", "clasificacion": "clasificacion", "grupo": "grupo", "horas": "horas_semanales", "estado": "activo", "fecha_alta": "created_at"}


def _aplicar_filtro_activos(query, model, activos):
    if activos == "true":
        return query.filter(model.deleted_at.is_(None), model.activo.is_(True))
    if activos == "false":
        return query.filter(or_(model.deleted_at.isnot(None), model.activo.is_(False)))
    return query


def _validar_listado(activos, tipo, page, per_page, sort, direction, ids):
    activos = str(activos or "true").strip().lower()
    tipo = str(tipo or "").strip().lower()
    sort = str(sort or "fecha_alta").strip().lower()
    direction = str(direction or "desc").strip().lower()
    if activos not in ACTIVOS_VALIDOS:
        raise ValidationError("El filtro de estado no es válido.")
    if tipo and tipo not in TIPOS_VALIDOS:
        raise ValidationError("La clase de personal no es válida.")
    if sort not in ORDENES:
        raise ValidationError("El campo de ordenamiento no es válido.")
    if direction not in {"asc", "desc"}:
        raise ValidationError("La dirección de ordenamiento no es válida.")
    if not isinstance(page, int) or page <= 0:
        raise ValidationError("La página debe ser un entero positivo.")
    if not isinstance(per_page, int) or per_page <= 0 or per_page > 9:
        raise ValidationError("La cantidad por página debe estar entre 1 y 9.")
    if ids is not None and (not isinstance(ids, list) or any(not isinstance(item, int) or item <= 0 for item in ids)):
        raise ValidationError("Los IDs deben ser enteros positivos.")
    return activos, tipo, sort, direction


def _consulta_unificada(activos, tipo):
    consultas = []
    if tipo in ("", "personal", "ptaa", "profesional"):
        query = db.session.query(
            Personal.id.label("id"), literal("personal").label("rol"), Personal.nombre_apellido.label("nombre_apellido"),
            TipoPersonal.nombre.label("clasificacion"), GrupoInvestigacionUtn.nombre_sigla_grupo.label("grupo"),
            Personal.horas_semanales.label("horas_semanales"), Personal.activo.label("activo"),
            Personal.fecha_alta_grupo.label("fecha_alta_grupo"), Personal.created_at.label("created_at"),
            Personal.updated_at.label("updated_at"), Personal.deleted_at.label("deleted_at"),
        ).outerjoin(TipoPersonal, Personal.tipo_personal_id == TipoPersonal.id).outerjoin(GrupoInvestigacionUtn, Personal.grupo_utn_id == GrupoInvestigacionUtn.id)
        consultas.append(_aplicar_filtro_activos(query, Personal, activos))
    if tipo in ("", "becario"):
        query = db.session.query(
            Becario.id.label("id"), literal("becario").label("rol"), Becario.nombre_apellido.label("nombre_apellido"),
            TipoFormacion.nombre.label("clasificacion"), GrupoInvestigacionUtn.nombre_sigla_grupo.label("grupo"),
            Becario.horas_semanales.label("horas_semanales"), Becario.activo.label("activo"),
            Becario.fecha_alta_grupo.label("fecha_alta_grupo"), Becario.created_at.label("created_at"),
            Becario.updated_at.label("updated_at"), Becario.deleted_at.label("deleted_at"),
        ).outerjoin(TipoFormacion, Becario.tipo_formacion_id == TipoFormacion.id).outerjoin(GrupoInvestigacionUtn, Becario.grupo_utn_id == GrupoInvestigacionUtn.id)
        consultas.append(_aplicar_filtro_activos(query, Becario, activos))
    if tipo in ("", "investigador"):
        query = db.session.query(
            Investigador.id.label("id"), literal("investigador").label("rol"), Investigador.nombre_apellido.label("nombre_apellido"),
            TipoDedicacion.nombre.label("clasificacion"), GrupoInvestigacionUtn.nombre_sigla_grupo.label("grupo"),
            Investigador.horas_semanales.label("horas_semanales"), Investigador.activo.label("activo"),
            Investigador.fecha_alta_grupo.label("fecha_alta_grupo"), Investigador.created_at.label("created_at"),
            Investigador.updated_at.label("updated_at"), Investigador.deleted_at.label("deleted_at"),
        ).outerjoin(TipoDedicacion, Investigador.tipo_dedicacion_id == TipoDedicacion.id).outerjoin(GrupoInvestigacionUtn, Investigador.grupo_utn_id == GrupoInvestigacionUtn.id)
        consultas.append(_aplicar_filtro_activos(query, Investigador, activos))
    return union_all(*(query.statement for query in consultas)).subquery("personal_unificado")


def listar_personal_paginado(*, activos="true", tipo=None, page=1, per_page=9, search=None, sort="fecha_alta", direction="desc", ids=None):
    activos, tipo, sort, direction = _validar_listado(activos, tipo, page, per_page, sort, direction, ids)
    source = _consulta_unificada(activos, tipo)
    query = db.session.query(source)
    term = str(search or "").strip().lower()
    if term:
        pattern = f"%{term}%"
        query = query.filter(or_(func.lower(source.c.nombre_apellido).like(pattern), func.lower(source.c.rol).like(pattern), func.lower(func.coalesce(source.c.clasificacion, "")).like(pattern), func.lower(func.coalesce(source.c.grupo, "")).like(pattern)))
    if ids is not None:
        query = query.filter(source.c.id.in_(ids)) if ids else query.filter(false())
    total = query.count()
    column = source.c[ORDENES[sort]]
    order = column.asc() if direction == "asc" else column.desc()
    rows = query.order_by(order, source.c.id.asc(), source.c.rol.asc()).offset((page - 1) * per_page).limit(per_page).all()
    data = []
    for row in rows:
        item = row._mapping
        data.append({
            "id": item["id"], "rol": item["rol"], "nombre_apellido": item["nombre_apellido"],
            "clasificacion": item["clasificacion"], "grupo": item["grupo"], "horas_semanales": item["horas_semanales"],
            "activo": item["activo"], "fecha_alta_grupo": item["fecha_alta_grupo"].isoformat() if item["fecha_alta_grupo"] else None,
            "created_at": item["created_at"].isoformat() if item["created_at"] else None,
            "updated_at": item["updated_at"].isoformat() if item["updated_at"] else None,
            "deleted_at": item["deleted_at"].isoformat() if item["deleted_at"] else None,
        })
    return {"data": data, "meta": {"page": page, "per_page": per_page, "total": total, "total_pages": (total + per_page - 1) // per_page}, "error": None}


def listar_personal_completo(activos: str = "true", tipo: str | None = None):
    """Contrato plano heredado; se conserva para consumidores sin paginación."""
    tipo_normalizado = (tipo or "").strip().lower()
    resultado = []
    if tipo_normalizado in ("", "personal", "ptaa", "profesional"):
        for item in _aplicar_filtro_activos(Personal.query, Personal, activos).all():
            resultado.append({**item.serialize(), "rol": "personal"})
    if tipo_normalizado in ("", "becario"):
        for item in _aplicar_filtro_activos(Becario.query, Becario, activos).all():
            resultado.append({**item.serialize(), "rol": "becario"})
    if tipo_normalizado in ("", "investigador"):
        for item in _aplicar_filtro_activos(Investigador.query, Investigador, activos).all():
            resultado.append({**item.serialize(), "rol": "investigador"})
    return sorted(resultado, key=lambda item: (item.get("created_at") or "", item["id"], item["rol"]), reverse=True)


def obtener_personal_por_tipo(tipo, id):
    modelos = {"personal": Personal, "ptaa": Personal, "profesional": Personal, "becario": Becario, "investigador": Investigador}
    tipo_normalizado = str(tipo).strip().lower()
    model = modelos.get(tipo_normalizado)
    if not model:
        raise ValidationError("La clase de personal no es válida.")
    registro = db.session.get(model, id)
    if not registro:
        raise NotFoundError("Personal no encontrado")
    return {**registro.serialize(), "rol": "personal" if model is Personal else tipo_normalizado}
