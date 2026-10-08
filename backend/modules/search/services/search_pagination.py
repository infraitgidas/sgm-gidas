"""Candidate selection for global search, before loading related objects."""

from datetime import date

from flask import g, has_request_context
from sqlalchemy import String, cast, func, literal, or_, select, union_all

from extension import db
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.directivos import Directivo, DirectivoGrupo
from modules.grupo.models.visita_grupo import VisitaAcademica
from modules.personal.models.personal import Personal, Becario, Investigador
from modules.personal.models.tipo_personal import TipoPersonal
from modules.produccion.models.actividad_docencia import ActividadDocencia
from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
from modules.produccion.models.documentacion_autores import Autor, DocumentacionBibliografica
from modules.produccion.models.registro_patente import RegistrosPropiedad, TipoRegistroPropiedad
from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor
from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica
from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato
from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, TipoProyecto
from modules.recursos.models.becas import Beca, Beca_Becario
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.models.movimiento_financiero import CategoriaErogacion, MovimientoFinanciero
from modules.shared.services.tenant_scope import _classes_by_table, _predicate
from modules.transferencia.models.transferencia_socio import TipoContrato, TransferenciaSocioProductiva


def _normalized(column):
    value = func.lower(cast(column, String))
    # SQLite has no unaccent and lower() leaves accented capitals unchanged.
    for accented, plain in (
        ("á", "a"), ("Á", "a"), ("é", "e"), ("É", "e"),
        ("í", "i"), ("Í", "i"), ("ó", "o"), ("Ó", "o"),
        ("ú", "u"), ("Ú", "u"), ("ñ", "n"), ("Ñ", "n"),
    ):
        value = func.replace(value, accented, plain)
    return value


def _matches(column, term):
    return _normalized(column).contains(term, autoescape=True)


def _specs(term):
    match = lambda *columns: or_(*(_matches(column, term) for column in columns))
    reunion_author = or_(
        TrabajoReunionAutor.investigador.has(_matches(Investigador.nombre_apellido, term)),
        TrabajoReunionAutor.becario.has(_matches(Becario.nombre_apellido, term)),
    )
    revista_author = or_(
        TrabajoRevistaAutor.investigador.has(_matches(Investigador.nombre_apellido, term)),
        TrabajoRevistaAutor.becario.has(_matches(Becario.nombre_apellido, term)),
    )
    return (
        (Personal, "Persona", Personal.nombre_apellido, None, match(Personal.nombre_apellido)),
        (Becario, "Becario", Becario.nombre_apellido, None, match(Becario.nombre_apellido)),
        (Beca, "Beca", Beca.nombre_beca, None, or_(
            match(Beca.nombre_beca, Beca.descripcion),
            Beca.fuente_financiamiento.has(_matches(FuenteFinanciamiento.nombre, term)),
            Beca.becarios.any(Beca_Becario.becario.has(_matches(Becario.nombre_apellido, term))),
        )),
        (Investigador, "Investigador", Investigador.nombre_apellido, None, match(Investigador.nombre_apellido)),
        (ActividadDocencia, "Actividad de Docencia", ActividadDocencia.curso, ActividadDocencia.fecha_inicio,
         match(ActividadDocencia.curso, ActividadDocencia.institucion)),
        (ProyectoInvestigacion, "Proyecto de Investigación", ProyectoInvestigacion.nombre_proyecto,
         ProyectoInvestigacion.fecha_inicio, match(ProyectoInvestigacion.nombre_proyecto,
                                                     ProyectoInvestigacion.descripcion_proyecto)),
        (TipoProyecto, "Tipo de Proyecto", TipoProyecto.nombre, None, match(TipoProyecto.nombre)),
        (Equipamiento, "Equipamiento", Equipamiento.denominacion, Equipamiento.fecha_incorporacion,
         match(Equipamiento.denominacion)),
        (DocumentacionBibliografica, "Documentación", DocumentacionBibliografica.titulo,
         DocumentacionBibliografica.fecha, match(DocumentacionBibliografica.titulo,
                                                  DocumentacionBibliografica.editorial)),
        (Autor, "Autor", Autor.nombre_apellido, None, match(Autor.nombre_apellido)),
        (CategoriaErogacion, "Categoría de Erogación", CategoriaErogacion.nombre, None,
         match(CategoriaErogacion.nombre)),
        (FuenteFinanciamiento, "Fuente de Financiamiento", FuenteFinanciamiento.nombre, None,
         match(FuenteFinanciamiento.nombre)),
        (ParticipacionRelevante, "Participación Relevante", ParticipacionRelevante.nombre_evento,
         ParticipacionRelevante.fecha, or_(
             match(ParticipacionRelevante.nombre_evento, ParticipacionRelevante.forma_participacion),
             ParticipacionRelevante.investigador.has(_matches(Investigador.nombre_apellido, term)),
             ParticipacionRelevante.becario.has(_matches(Becario.nombre_apellido, term)),
         )),
        (RegistrosPropiedad, "Registro de Propiedad", RegistrosPropiedad.nombre_articulo,
         RegistrosPropiedad.fecha_registro, match(RegistrosPropiedad.nombre_articulo,
                                                   RegistrosPropiedad.organismo_registrante)),
        (TipoRegistroPropiedad, "Tipo Registro Propiedad", TipoRegistroPropiedad.nombre, None,
         match(TipoRegistroPropiedad.nombre)),
        (TransferenciaSocioProductiva, "Transferencia Socio Productiva",
         TransferenciaSocioProductiva.descripcion_actividad, TransferenciaSocioProductiva.fecha_inicio,
         match(TransferenciaSocioProductiva.descripcion_actividad, TransferenciaSocioProductiva.demandante)),
        (TipoContrato, "Tipo de Contrato", TipoContrato.nombre, None, match(TipoContrato.nombre)),
        (TipoPersonal, "Tipo Personal", TipoPersonal.nombre, None, match(TipoPersonal.nombre)),
        (TrabajoReunionCientifica, "Trabajo en Reunión Científica", TrabajoReunionCientifica.titulo_trabajo,
         TrabajoReunionCientifica.fecha_presentacion, or_(
             match(TrabajoReunionCientifica.titulo_trabajo, TrabajoReunionCientifica.nombre_reunion,
                   TrabajoReunionCientifica.procedencia),
             TrabajoReunionCientifica.autorias.any(reunion_author),
         )),
        (TrabajosRevistasReferato, "Trabajo en Revista con Referato", TrabajosRevistasReferato.titulo_trabajo,
         TrabajosRevistasReferato.fecha_publicacion, or_(
             match(TrabajosRevistasReferato.titulo_trabajo, TrabajosRevistasReferato.nombre_revista,
                   TrabajosRevistasReferato.editorial, TrabajosRevistasReferato.issn, TrabajosRevistasReferato.pais),
             TrabajosRevistasReferato.autorias.any(revista_author),
         )),
        (Directivo, "Directivo", Directivo.nombre_apellido,
         select(DirectivoGrupo.fecha_inicio).where(
             DirectivoGrupo.id_directivo == Directivo.id, DirectivoGrupo.fecha_fin.is_(None)
         ).order_by(DirectivoGrupo.fecha_inicio.desc()).limit(1).scalar_subquery(),
         match(Directivo.nombre_apellido)),
        (ArticuloDivulgacion, "Artículo de Divulgación", ArticuloDivulgacion.titulo,
         ArticuloDivulgacion.fecha_publicacion, match(ArticuloDivulgacion.titulo, ArticuloDivulgacion.descripcion)),
        (MovimientoFinanciero, "Movimiento financiero",
         literal("Movimiento ") + cast(MovimientoFinanciero.numero_movimiento, String), MovimientoFinanciero.fecha,
         or_(
             match(MovimientoFinanciero.numero_movimiento, MovimientoFinanciero.tipo_movimiento),
             MovimientoFinanciero.categoria_erogacion.has(_matches(CategoriaErogacion.nombre, term)),
             MovimientoFinanciero.fuente_financiamiento.has(_matches(FuenteFinanciamiento.nombre, term)),
         )),
        (VisitaAcademica, "Visita Académica", VisitaAcademica.razon, VisitaAcademica.fecha,
         match(VisitaAcademica.razon, VisitaAcademica.procedencia)),
    )


def page_hits(term, orden, eliminados, page, per_page):
    scopes = _classes_by_table() if has_request_context() and getattr(g, "current_grupo_utn_id", None) else None
    group_id = getattr(g, "current_grupo_utn_id", None) if scopes is not None else None
    queries = []
    for position, (model, kind, title, event_date, predicate) in enumerate(_specs(term)):
        query = select(
            literal(kind).label("kind"), model.id.label("record_id"),
            cast(title, String).label("title"),
            cast(event_date, String).label("event_date") if event_date is not None
            else literal(None).label("event_date"),
            (model.deleted_at.isnot(None) if hasattr(model, "deleted_at") else literal(False)).label("inactive"),
            literal(position).label("position"),
        ).where(predicate)
        if hasattr(model, "deleted_at") and eliminados != "all":
            query = query.where(model.deleted_at.isnot(None) if eliminados == "true"
                                else model.deleted_at.is_(None))
        if model is Directivo:
            query = query.where(Directivo.participaciones_grupo.any(DirectivoGrupo.fecha_fin.is_(None)))
        if scopes is not None:
            scope = _predicate(model, group_id, scopes)
            if scope is not None:
                query = query.where(scope)
        queries.append(query)
    hits = union_all(*queries).subquery()
    total = db.session.scalar(select(func.count()).select_from(hits))
    if orden == "alf_asc":
        ordering = (hits.c.inactive.asc(), func.lower(hits.c.title).asc())
    elif orden == "alf_desc":
        ordering = (hits.c.inactive.desc(), func.lower(hits.c.title).desc())
    elif orden == "fecha_desc":
        ordering = (func.coalesce(hits.c.event_date, str(date.min)).desc(),)
    elif orden == "fecha_asc":
        ordering = (func.coalesce(hits.c.event_date, str(date.min)).asc(),)
    else:
        ordering = ()
    rows = db.session.execute(
        select(hits.c.kind, hits.c.record_id).order_by(*ordering, hits.c.position.asc(), hits.c.record_id.asc())
        .offset((page - 1) * per_page).limit(per_page)
    ).all()
    return rows, total
