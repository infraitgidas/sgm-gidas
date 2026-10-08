"""Escenario institucional 2025/2026 para validar memorias desde la interfaz.

La limpieza y carga son una única transacción. No crea memorias ni exporta Excel.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATES = (date(2026, 1, 20), date(2026, 3, 18), date(2026, 5, 15), date(2026, 7, 22), date(2026, 9, 24), date(2026, 10, 2))
PAST = (date(2025, 3, 18), date(2025, 9, 24))
TOPICS = (
    ("Arquitecturas de software", "Diseño y evaluación de arquitecturas de servicios para plataformas institucionales"),
    ("Inteligencia artificial", "Modelos de aprendizaje automático para el análisis de indicadores de producción y salud"),
    ("Interacción persona computadora", "Accesibilidad y evaluación de experiencia de uso en entornos educativos digitales"),
    ("Informática en salud", "Interoperabilidad y calidad de datos para el seguimiento de procesos asistenciales"),
    ("Tecnologías educativas", "Analítica del aprendizaje y recursos digitales para la formación en ingeniería"),
)
NAMES = ("Lucía Valentina Herrera", "Martín Andrés Quiroga", "Camila Soledad Benítez", "Federico Nicolás Acosta", "Julieta Gabriela Romero")
SURNAMES = ("Herrera", "Quiroga", "Benítez", "Acosta", "Romero")
SOURCES = ("Universidad Tecnológica Nacional", "CONICET", "Agencia I+D+i", "Comisión de Investigaciones Científicas", "Fundación de Vinculación Tecnológica")


def paragraph(index):
    area, title = TOPICS[index % 5]
    return (f"{title}. La línea de {area.lower()} articula investigación aplicada, formación de recursos humanos "
            "y transferencia al medio socio productivo. Durante el período se relevaron necesidades de las "
            "instituciones participantes, se diseñaron prototipos y se evaluaron resultados mediante indicadores "
            "de calidad, accesibilidad y reproducibilidad. El equipo documentó los procedimientos y preparó "
            "materiales para su comunicación en reuniones científicas y actividades de capacitación.")


def validate_environment(group_id, user_id):
    from flask import current_app
    from extension import db
    from modules.auth.models.usuario import Usuario
    from modules.grupo.models.grupo import GrupoInvestigacionUtn
    if current_app.config.get("APP_ENV") not in {"testing", "development", "local", "docker"}:
        raise RuntimeError("La seed solo puede ejecutarse en una base de desarrollo o testing")
    group, user = db.session.get(GrupoInvestigacionUtn, group_id), db.session.get(Usuario, user_id)
    if not group or group.deleted_at is not None or group.nombre_sigla_grupo.strip() != "GIDAS":
        raise RuntimeError("Seleccione la UCT GIDAS activa; no se reemplazan otras UCT")
    if not user or user.deleted_at is not None or not user.activo or user.rol.nombre != "ADMIN":
        raise RuntimeError("La auditoría de la carga requiere un ADMIN activo")
    if DATES[-1] > date.today():
        raise RuntimeError("El escenario necesita que todas las fechas de hechos hayan ocurrido")
    return group


def cleanup_plan(group_id):
    """Selecciona hechos de 2026, intervalos que lo cruzan y antiguos textos TEST.

    Usa las FK para limpiar dependencias y rechaza borrar snapshots de otras memorias.
    Usuarios, catálogos, identidades, otras UCT y memorias de otros años no son raíces.
    """
    from sqlalchemy import and_, or_, select
    from extension import db
    tables = db.metadata.tables
    chosen = {}
    start, end = date(2026, 1, 1), date(2026, 12, 31)
    point = {"equipamiento_grupo": "fecha_incorporacion", "documentacion_bibliografica": "fecha",
             "articulo_divulgacion": "fecha_publicacion", "trabajo_reunion_cientifica": "fecha_presentacion",
             "trabajos_revista": "fecha_publicacion", "registros_patente_grupo": "fecha_registro",
             "visita_grupo": "fecha", "movimiento_financiero": "fecha", "erogacion": "fecha"}
    intervals = {"proyecto_investigacion", "transferencia_socio_productiva", "beca", "investigador", "becario", "personal"}
    for name in (*point, *sorted(intervals), "memoria", "planificacion_grupo", "directivo", "adoptante"):
        table = tables[name]
        group_field = "grupo_id" if "grupo_id" in table.c else "grupo_utn_id"
        conditions = []
        if name in point:
            conditions.append(table.c[point[name]].between(start, end))
        elif name in intervals:
            field = "fecha_inicio" if "fecha_inicio" in table.c else "fecha_alta_grupo"
            conditions.append(table.c[field].between(start, end))
            if "fecha_fin" in table.c:
                conditions.append(table.c.fecha_fin.between(start, end))
        elif name == "memoria":
            conditions.append(and_(table.c.periodo_inicio <= end, table.c.periodo_fin >= start))
        elif name == "planificacion_grupo":
            conditions.append(table.c.anio == 2026)
        # Los datos con etiquetas heredadas no deben contaminar la comparación formal.
        if name not in {"memoria", "planificacion_grupo"}:
            for column in table.c:
                if column.name in {"nombre_apellido", "nombre_beca", "nombre_proyecto", "denominacion", "nombre", "titulo", "titulo_trabajo"}:
                    conditions.append(column.ilike("%TEST%"))
        if conditions:
            rows = list(db.session.execute(select(table.c.id).where(table.c[group_field] == group_id, or_(*conditions))).scalars())
            if rows:
                chosen[name] = set(rows)
    # Entidades con UCT indirecta.
    investigator = tables["investigador"]
    project = tables["proyecto_investigacion"]
    for name, field, parent, fk in (("participacion_relevante", "fecha", investigator, "investigador_id"),
                                  ("actividad_y_catedra_posgrado", "fecha_inicio", investigator, "investigador_id"),
                                  ("distincion_recibida", "fecha", project, "proyecto_investigacion_id")):
        table = tables[name]
        parent_ids = select(parent.c.id).where(parent.c.grupo_utn_id == group_id)
        dates = table.c[field].between(start, end)
        if "fecha_fin" in table.c:
            dates = or_(dates, table.c.fecha_fin.between(start, end))
        rows = set(db.session.execute(select(table.c.id).where(table.c[fk].in_(parent_ids), dates)).scalars())
        if name == "participacion_relevante":
            scholar = tables["becario"]
            rows.update(db.session.execute(select(table.c.id).where(table.c.becario_id.in_(
                select(scholar.c.id).where(scholar.c.grupo_utn_id == group_id)), dates)).scalars())
        if rows:
            chosen[name] = rows
    # Mandatos: tampoco deben sobrevivir autoridades anteriores que se superpongan con la seed.
    table = tables["directivo_grupo"]
    ids = set(db.session.execute(select(table.c.id).where(table.c.id_grupo_utn == group_id,
        table.c.fecha_inicio <= end, or_(table.c.fecha_fin.is_(None), table.c.fecha_fin >= start))).scalars())
    if ids:
        chosen[table.name] = ids
    protected_memorias = set(db.session.execute(select(tables["memoria_version"].c.id).where(
        ~tables["memoria_version"].c.memoria_id.in_(chosen.get("memoria", set())))).scalars())
    archived = {}
    # Una entidad respaldada por otra memoria no se borra físicamente. Su
    # vigencia de negocio se retira de 2026 y la foto histórica queda intacta.
    for table in tables.values():
        if "memoria_version_id" not in table.c:
            continue
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent not in chosen or parent == "memoria_version":
                continue
            ids = set(db.session.execute(select(fk.parent).where(fk.parent.in_(chosen[parent]),
                table.c.memoria_version_id.in_(protected_memorias))).scalars())
            if ids:
                if "fecha_fin" not in tables[parent].c:
                    raise RuntimeError(f"La limpieza afectaría historia de otro año en {parent}; no se aplicó")
                archived.setdefault(parent, set()).update(ids)
                chosen[parent] -= ids
    chosen = {name: ids for name, ids in chosen.items() if ids}
    changed = True
    while changed:
        changed = False
        for table in tables.values():
            if table.name == "memoria":  # La FK version_actual_id crea un ciclo ya seleccionado.
                continue
            for fk in table.foreign_keys:
                parent = fk.column.table.name
                if parent not in chosen or fk.column.name != "id":
                    continue
                if "id" not in table.c:
                    continue  # autorxlibro se elimina por sus claves compuestas al aplicar.
                rows = set(db.session.execute(select(table.c.id).where(fk.parent.in_(chosen[parent]))).scalars())
                if "memoria_version_id" in table.c and rows:
                    protected = db.session.execute(select(table.c.id).where(table.c.id.in_(rows),
                        table.c.memoria_version_id.in_(protected_memorias))).first()
                    if protected:
                        raise RuntimeError(f"La limpieza afectaría historia de otro año en {table.name}; no se aplicó")
                new = rows - chosen.get(table.name, set())
                if new:
                    chosen.setdefault(table.name, set()).update(new)
                    changed = True
    return chosen, archived


def apply_cleanup(chosen, archived, user_id):
    from sqlalchemy import delete, update
    from extension import db
    tables = db.metadata.tables
    if chosen.get("memoria"):
        db.session.execute(update(tables["memoria"]).where(tables["memoria"].c.id.in_(chosen["memoria"])).values(version_actual_id=None))
    pending, done = set(chosen), set()

    def remove(name):
        if name in done:
            return
        done.add(name)
        for child in tables.values():
            if child.name == "memoria":
                continue
            for fk in child.foreign_keys:
                if fk.column.table.name != name:
                    continue
                if child.name in pending:
                    remove(child.name)
                elif "id" not in child.c:
                    db.session.execute(delete(child).where(fk.parent.in_(chosen[name])))
        table = tables[name]
        db.session.execute(delete(table).where(table.c.id.in_(chosen[name])))

    for name in sorted(pending):
        remove(name)
    from modules.shared.models.auditoria_campo import AuditoriaCampo
    now = datetime.utcnow()
    for name, ids in archived.items():
        table = tables[name]
        for item_id in ids:
            previous = db.session.execute(table.select().where(table.c.id == item_id)).mappings().one()
            db.session.add(AuditoriaCampo(entidad=name, registro_id=item_id, campo="fecha_fin",
                valor_anterior=str(previous["fecha_fin"]), valor_nuevo="2025-12-31", usuario_id=user_id))
        db.session.execute(update(table).where(table.c.id.in_(ids)).values(fecha_fin=date(2025, 12, 31),
            activo=False, deleted_at=now, deleted_by=user_id, updated_at=now, updated_by=user_id))
    db.session.expire_all()


def populate(group_id, user_id, *, replace=False, dry_run=False):
    from sqlalchemy import func
    from extension import db
    from modules import models_registry  # noqa: F401
    from modules.catalogos.models.categoria_utn import CategoriaUtn
    from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
    from modules.grupo.models.directivos import Cargo, Directivo, DirectivoGrupo
    from modules.grupo.models.programa_actividades import PlanificacionGrupo
    from modules.grupo.models.programa_incentivos import ProgramaIncentivos
    from modules.grupo.models.visita_grupo import VisitaAcademica, TipoVisita
    from modules.personal.models.identidad import IdentidadPersonal
    from modules.personal.models.personal import (Investigador, Becario, Personal, TipoDedicacion, TipoFormacion,
        InvestigadorHorasHistorial, BecarioHorasHistorial, PersonalHorasHistorial)
    from modules.personal.models.tipo_personal import TipoPersonal
    from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, TipoProyecto, InvestigadorProyecto, BecarioProyecto
    from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
    from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
    from modules.produccion.models.actividad_docencia import ActividadDocencia, GradoAcademico, InvestigadorActividadGrado, RolActividad
    from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
    from modules.produccion.models.documentacion_autores import DocumentacionBibliografica, Autor
    from modules.produccion.models.distinciones import DistincionRecibida
    from modules.produccion.models.registro_patente import RegistrosPropiedad
    from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica, TipoReunion
    from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato, TipoRevista
    from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor
    from modules.produccion.services.tipo_registro_service import TipoRegistroPropiedad
    from modules.recursos.models.equipamiento import Equipamiento
    from modules.recursos.models.becas import Beca, Beca_Becario
    from modules.recursos.models.movimiento_financiero import CategoriaErogacion, MovimientoFinanciero
    from modules.transferencia.models.transferencia_socio import TransferenciaSocioProductiva, TipoContrato, Adoptante, AdoptanteTransferencia
    from modules.grupo.services.directivo_service import DirectivoGrupoService
    from modules.shared.services.date_time import validate_institutional_date
    from modules.recursos.services.saldo_financiero_service import SaldoFinancieroService

    group = validate_environment(group_id, user_id)
    sentinel = "GIDAS202601"
    if not replace and ProyectoInvestigacion.query.filter_by(grupo_utn_id=group_id, codigo_proyecto=sentinel).first():
        return {"created": False, "grupo_id": group_id, "motivo": "El escenario ya está cargado"}
    cleanup, archived = cleanup_plan(group_id) if replace else ({}, {})
    if dry_run:
        return {"limpieza": {name: len(ids) for name, ids in sorted(cleanup.items())},
                "archivados_para_preservar_historia": {name: sorted(ids) for name, ids in archived.items()}, "fechas_2026": [str(d) for d in DATES],
                "secciones": "5 registros de 2026 por subtipo y controles de 2025; no crea memorias ni informes"}
    result = defaultdict(list)

    def add(model, **values):
        lookup = {key: value for key, value in values.items() if key not in {"created_by", "numero_movimiento", "numero_transferencia"}
                  and isinstance(value, (str, int, float, Decimal, date, type(None))) and hasattr(model, key)}
        if lookup and model is not IdentidadPersonal:
            existing = model.query.filter_by(**lookup).first()
            if existing:
                return existing
        if hasattr(model, "created_by"):
            values.setdefault("created_by", user_id)
        for key, value in values.items():
            if isinstance(value, date) and not isinstance(value, datetime):
                validate_institutional_date(value, key, allow_future=key in {"fecha_fin", "fecha_fin_original"})
        item = model(**values)
        db.session.add(item)
        db.session.flush()
        result[model.__tablename__].append(item.id)
        return item

    def catalog(model, name, **values):
        item = model.query.filter_by(nombre=name, **values).first()
        if item and item.deleted_at is not None:
            item.restore()
            item.mark_updated(user_id)
        return item or add(model, nombre=name, **values)

    identity_number = int(db.session.query(func.max(IdentidadPersonal.dni)).scalar() or 88000000)
    identity_number = max(identity_number, 88000000)

    def identity():
        nonlocal identity_number
        identity_number += 1
        dni = str(identity_number)
        base = "20" + dni
        digit = 11 - sum(int(c) * weight for c, weight in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
        digit = 0 if digit == 11 else 9 if digit == 10 else digit
        return add(IdentidadPersonal, dni=dni, cuil=f"20-{dni}-{digit}")

    try:
        if cleanup or archived:
            apply_cleanup(cleanup, archived, user_id)
        group = validate_environment(group_id, user_id)
        group.objetivo_desarrollo = ("El GIDAS promueve la investigación y el desarrollo aplicado a sistemas informáticos y "
            "computacionales mediante proyectos de software, inteligencia artificial, informática en salud y tecnologías "
            "educativas. Sus actividades articulan formación de recursos humanos, producción científica y transferencia "
            "a instituciones públicas y organizaciones del medio socio productivo. Se priorizan la accesibilidad, la "
            "calidad de los datos y la reproducibilidad de los resultados, con cooperación interdisciplinaria y "
            "participación de investigadores, becarios y personal técnico.")
        group.mark_updated(user_id)
        funding = [catalog(FuenteFinanciamiento, name) for name in SOURCES]
        # Cinco mandatos sucesivos válidos, nunca cinco autoridades simultáneas.
        mandates = ((date(2025, 1, 1), date(2025, 12, 31), "Director", NAMES[0]),
                    (date(2026, 1, 1), date(2026, 3, 31), "Director", NAMES[1]),
                    (date(2026, 4, 1), date(2026, 6, 30), "Director", NAMES[2]),
                    (date(2026, 7, 1), None, "Director", NAMES[3]),
                    (date(2025, 1, 1), None, "Vicedirector", NAMES[4]))
        for start, end, role, name in mandates:
            directivo = add(Directivo, nombre_apellido=name, grupo_utn_id=group_id)
            payload = {"id_directivo": directivo.id, "id_grupo_utn": group_id, "id_cargo": catalog(Cargo, role).id,
                       "fecha_inicio": str(start), "fecha_fin": str(end) if end else None}
            existing = DirectivoGrupo.query.filter_by(id_directivo=directivo.id, id_grupo_utn=group_id,
                id_cargo=payload["id_cargo"], fecha_inicio=start, fecha_fin=end, deleted_at=None).first()
            if not existing:
                DirectivoGrupoService.asignar_a_grupo(payload, user_id, commit=False)
        investigators = []
        for index, name in enumerate(NAMES):
            start = date(2025, 1, 1) if index < 2 else DATES[index]
            inv = add(Investigador, nombre_apellido=name, identidad=identity(), grupo_utn_id=group_id,
                fecha_alta_grupo=start, horas_semanales=12 + index * 4,
                categoria_utn_id=catalog(CategoriaUtn, ("Investigador formado", "Investigador en formación")[index % 2]).id,
                programa_incentivos_id=catalog(ProgramaIncentivos, ("Categoría I", "Categoría II", "Categoría III")[index % 3]).id,
                tipo_dedicacion_id=catalog(TipoDedicacion, ("Exclusiva", "Semiexclusiva", "Simple")[index % 3]).id)
            add(InvestigadorHorasHistorial, investigador_id=inv.id, horas_semanales=inv.horas_semanales, fecha_inicio=start)
            investigators.append(inv)
        for category in ("Profesional", "Técnico, administrativo y de apoyo"):
            for index in range(5):
                start = date(2025, 2, 1) if index == 0 else DATES[index]
                person = add(Personal, nombre_apellido=f"{('María Elena' if category == 'Profesional' else 'Pablo Esteban')} {SURNAMES[index]}",
                    identidad=identity(), grupo_utn_id=group_id, fecha_alta_grupo=start, horas_semanales=15 + index * 3,
                    tipo_personal_id=catalog(TipoPersonal, category).id)
                add(PersonalHorasHistorial, personal_id=person.id, horas_semanales=person.horas_semanales, fecha_inicio=start)
        scholarships = [add(Beca, grupo_utn_id=group_id, nombre_beca=f"Programa de formación en {TOPICS[i][0].lower()}",
            descripcion=paragraph(i), fecha_alta_grupo=date(2025, 1, 1), fuente_financiamiento_id=funding[i].id) for i in range(5)]
        scholars = []
        for form_index, form in enumerate(("Doctorado", "Maestría/Especialización", "Graduado", "Alumno", "Pasante", "Tesina")):
            for index in range(5):
                start = date(2025, 3, 1) if index == 0 else DATES[index]
                name = f"{('Sofía', 'Tomás', 'Valentina', 'Santiago', 'Catalina', 'Joaquín')[form_index]} {('Victoria', 'Manuel', 'Lucía', 'Andrés', 'Paula')[index]} {SURNAMES[index]}"
                scholar = add(Becario, nombre_apellido=name, identidad=identity(), grupo_utn_id=group_id,
                    fecha_alta_grupo=start, horas_semanales=10 + index * 2, tipo_formacion_id=catalog(TipoFormacion, form).id)
                add(BecarioHorasHistorial, becario_id=scholar.id, horas_semanales=scholar.horas_semanales, fecha_inicio=start)
                add(Beca_Becario, id_beca=scholarships[index].id, id_becario=scholar.id, fecha_inicio=start,
                    fecha_fin=None, monto_percibido=85000 + index * 15000)
                scholars.append(scholar)
        projects = []
        for index in range(10):
            start = date(2025, 2 if index == 0 else 2 * (index % 5) + 1, 1) if index < 5 else DATES[index % 5]
            duration = (12, 18, 24, 30, 36)[index % 5]
            finish = ProyectoInvestigacionService._fin_inclusivo(start, duration)
            payload = {"codigo_proyecto": f"GIDAS2026{index + 1:02d}", "nombre_proyecto": TOPICS[index % 5][1],
                "descripcion_proyecto": paragraph(index), "dificultades_proyecto": "La heterogeneidad de los datos y la coordinación de las instituciones requieren procedimientos comunes de validación y seguimiento.",
                "fecha_inicio": str(start), "fecha_fin": str(finish), "monto_destinado": 750000 + index * 125000,
                "tipo_proyecto_id": catalog(TipoProyecto, ("PID", "PICT", "PDTS", "Proyecto de innovación", "Proyecto de vinculación")[index % 5]).id,
                "fuente_financiamiento_id": funding[index % 5].id, "grupo_utn_id": group_id}
            project = ProyectoInvestigacion.query.filter_by(grupo_utn_id=group_id, codigo_proyecto=payload["codigo_proyecto"]).first()
            if not project:
                created = ProyectoInvestigacionService.create(payload, user_id, commit=False)
                project = db.session.get(ProyectoInvestigacion, created["id"])
                result[ProyectoInvestigacion.__tablename__].append(project.id)
            projects.append(project)
            inv = investigators[index % 2] if index < 5 else investigators[index % 5]
            relation_start = max(start, inv.fecha_alta_grupo)
            add(InvestigadorProyecto, id_investigador=inv.id, id_proyecto=project.id, fecha_inicio=relation_start,
                fecha_fin=finish, es_coordinador=True)
            scholar = scholars[(index % 6) * 5]
            add(BecarioProyecto, id_becario=scholar.id, id_proyecto=project.id,
                fecha_inicio=max(start, scholar.fecha_alta_grupo), fecha_fin=finish)
        for index, day in enumerate((*PAST, *DATES)):
            topic_index = (index - 2) % 5
            topic = TOPICS[topic_index]
            label = f"{topic[0]}: recursos y resultados {day.year}"
            equipo = add(Equipamiento, grupo_utn_id=group_id, denominacion=f"Estación de trabajo para {topic[0].lower()} {day.year}",
                fecha_incorporacion=day, monto_invertido=250000 + index * 45000,
                descripcion_breve=f"Plataforma de cómputo con procesador multinúcleo, almacenamiento de estado sólido y herramientas para {topic[0].lower()}. " + paragraph(topic_index))
            author = Autor.query.filter_by(nombre_apellido=NAMES[topic_index], grupo_utn_id=group_id, deleted_at=None).first()
            author = author or add(Autor, nombre_apellido=NAMES[topic_index], grupo_utn_id=group_id)
            doc = add(DocumentacionBibliografica, grupo_id=group_id, titulo=label, editorial="Ediciones Académicas del Plata",
                anio=day.year, fecha=day)
            if author not in doc.autores:
                doc.autores.append(author)
            inv = investigators[topic_index] if day.year == 2026 else investigators[index % 2]
            # La fecha de una actividad nunca precede al alta de su participante.
            inv = investigators[0] if inv.fecha_alta_grupo > day else inv
            activity = add(ActividadDocencia, investigador_id=inv.id, curso=f"Seminario de {topic[0].lower()}",
                institucion="Universidad Tecnológica Nacional, Facultad Regional La Plata", fecha_inicio=day,
                fecha_fin=date(day.year, 12, 20), rol_actividad_id=catalog(RolActividad, "Docente responsable").id)
            add(InvestigadorActividadGrado, investigador_id=inv.id, actividad_docencia_id=activity.id,
                grado_academico_id=catalog(GradoAcademico, ("Doctor", "Magíster", "Ingeniero")[topic_index % 3]).id, fecha_inicio=day)
            for section in ("Jornada de investigación", "Curso de actualización", "Gestión interna", "Organización de encuentro"):
                add(ParticipacionRelevante, investigador_id=inv.id, fecha=day,
                    nombre_evento=f"{section} sobre {topic[0].lower()} ({day.year})",
                    forma_participacion=paragraph(topic_index))
            for kind in ("Nacional con referato", "Internacional con referato"):
                work = add(TrabajoReunionCientifica, grupo_utn_id=group_id, tipo_reunion_id=catalog(TipoReunion, kind).id,
                    titulo_trabajo=topic[1], nombre_reunion=f"Congreso de {topic[0].lower()} {day.year}",
                    procedencia="La Plata, Argentina" if kind.startswith("Nacional") else "Montevideo, Uruguay",
                    fecha_presentacion=day)
                add(TrabajoReunionAutor, trabajo_id=work.id, investigador_id=inv.id)
            for kind in ("Revista con referato", "Libro o capítulo de libro"):
                work = add(TrabajosRevistasReferato, grupo_utn_id=group_id, tipo_revista_id=catalog(TipoRevista, kind).id,
                    titulo_trabajo=topic[1], nombre_revista=f"Estudios en {topic[0].lower()}", editorial="Editorial Universitaria del Plata",
                    pais="Argentina", issn="1234-5679", fecha_publicacion=day)
                add(TrabajoRevistaAutor, trabajo_id=work.id, investigador_id=inv.id)
            add(ArticuloDivulgacion, grupo_utn_id=group_id, titulo=label, descripcion=paragraph(topic_index), fecha_publicacion=day)
            for kind in ("Patente", "Propiedad intelectual", "Propiedad industrial"):
                add(RegistrosPropiedad, grupo_utn_id=group_id, tipo_registro_id=catalog(TipoRegistroPropiedad, kind).id,
                    nombre_articulo=f"{topic[1]}: {kind.lower()} ({day.year})", organismo_registrante="Instituto Nacional de la Propiedad Industrial" if kind != "Propiedad intelectual" else "Dirección Nacional del Derecho de Autor", fecha_registro=day)
            active_project = next(project for project in projects if project.fecha_inicio <= day <= project.fecha_fin)
            add(DistincionRecibida, fecha=day, proyecto_investigacion_id=active_project.id,
                descripcion=f"Reconocimiento académico a {topic[1].lower()}, otorgado por su contribución a la investigación aplicada y la formación de recursos humanos.")
            add(VisitaAcademica, grupo_utn_id=group_id, fecha=day, tipo_visita_id=catalog(TipoVisita, "Cooperación científica").id,
                procedencia=f"Universidad del Litoral, equipo de {topic[0].lower()}", razon=paragraph(topic_index))
        adoptantes = [catalog(Adoptante, name, grupo_utn_id=group_id) for name in (
            "Municipalidad de La Plata", "Hospital Regional del Sur", "Cooperativa Tecnológica del Plata", "Instituto de Formación Técnica", "Fundación para la Innovación Educativa")]
        transfer_number = db.session.query(func.max(TransferenciaSocioProductiva.numero_transferencia)).scalar() or 0
        for kind in ("Transferencia de tecnología", "I+D+i", "Transferencia de conocimientos", "Asistencia técnica o consultoría", "Servicios técnicos", "Difusión a la comunidad"):
            for index, day in enumerate((*PAST, *DATES)):
                transfer_number += 1
                transfer = add(TransferenciaSocioProductiva, grupo_utn_id=group_id, numero_transferencia=transfer_number,
                    denominacion=f"{kind} en {TOPICS[index % 5][0].lower()} ({day.year})", demandante=adoptantes[index % 5].nombre,
                    descripcion_actividad=paragraph(index), monto=180000 + index * 30000,
                    fecha_inicio=day, fecha_fin=date(day.year + 1, day.month, day.day), tipo_contrato_id=catalog(TipoContrato, kind).id)
                add(AdoptanteTransferencia, transferencia_id=transfer.id, adoptante_id=adoptantes[index % 5].id)
        categories = {code: CategoriaErogacion.query.filter_by(codigo=code).first() or add(CategoriaErogacion, codigo=code, nombre=name)
                      for code, name in (("CORRIENTE", "Corriente"), ("CAPITAL", "Capital"))}
        number = db.session.query(func.max(MovimientoFinanciero.numero_movimiento)).filter_by(grupo_utn_id=group_id).scalar() or 0
        for index, day in enumerate((*PAST, *DATES)):
            source = funding[index % 5]
            for kind, code, value in (("INGRESO", None, "1600000.00"), ("EGRESO", "CORRIENTE", "125000.00"), ("EGRESO", "CAPITAL", "275000.00")):
                number += 1
                if kind == "EGRESO" and SaldoFinancieroService.saldo_de_fuente(group_id, source.id) < Decimal(value):
                    raise RuntimeError("Saldo insuficiente en la fuente; la transacción se revierte")
                add(MovimientoFinanciero, grupo_utn_id=group_id, numero_movimiento=number, fecha=day,
                    tipo_movimiento=kind, monto=Decimal(value), moneda="ARS", monto_equivalente_ars=Decimal(value),
                    fuente_financiamiento_id=source.id, categoria_erogacion_id=categories[code].id if code else None)
        # Una planificación anual integra cinco líneas, sin duplicar el año en UI.
        for year in (2027,):
            existing = PlanificacionGrupo.query.filter_by(grupo_id=group_id, anio=year, deleted_at=None).first()
            value = "\n\n".join(f"{i + 1}. {paragraph(i)}" for i in range(5))
            if existing:
                existing.descripcion = value
                existing.mark_updated(user_id)
            else:
                add(PlanificacionGrupo, grupo_id=group_id, anio=year, descripcion=value)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {"created": True, "grupo_id": group_id, "eliminados": {name: len(ids) for name, ids in sorted(cleanup.items())},
            "archivados_para_preservar_historia": {name: sorted(ids) for name, ids in archived.items()},
            "creados": {name: len(ids) for name, ids in sorted(result.items())}, "ids": dict(result),
            "fechas_2026": [str(day) for day in DATES], "controles_2025": [str(day) for day in PAST],
            "memorias_creadas": 0, "excel_generado": False,
            "notas": ["El equipo directivo solo admite Director y Vicedirector: cinco mandatos históricos, dos actuales.",
                      "Cinco líneas en una planificación 2027. Los informes PID requieren primero una memoria creada por el usuario."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group-id", type=int, required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--replace-2026", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    from app import app
    with app.app_context():
        result = populate(args.group_id, args.user_id, replace=args.replace_2026, dry_run=not args.apply)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
