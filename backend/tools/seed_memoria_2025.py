"""Seed optativa del documento institucional, independiente de la seed genérica."""
import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.memoria_2025_dataset import SOURCE, amount, first_date, read_dataset, text


def name_key(value):
    value = unicodedata.normalize("NFKD", text(value)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\b(dra?|ing|mag|prof)\b\.?", "", value)
    value = value.split("(", 1)[0]
    value = value.replace("enmanuel", "emanuel").replace("emmanuel", "emanuel").replace("quiros", "quiroz")
    key = " ".join(sorted(re.findall(r"[a-z]+", value)))
    return {"mirta penalva": "carmen del mirta penalva", "leopoldo nahuel": "eduardo leopoldo nahuel"}.get(key, key)


def seed_memoria_2025(user_id, dataset=None):
    """Carga entidades vivas. Nunca borra datos ni escribe snapshots manualmente."""
    from flask import current_app
    from extension import db
    from modules.auth.models.usuario import Usuario
    from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
    from modules.catalogos.models.categoria_utn import CategoriaUtn
    from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
    from modules.grupo.models.grupo import GrupoInvestigacionUtn
    from modules.grupo.models.directivos import Cargo, Directivo, DirectivoGrupo
    from modules.grupo.models.programa_actividades import PlanificacionGrupo
    from modules.grupo.models.programa_incentivos import ProgramaIncentivos
    from modules.informes.models.informe import Informe, InformeProyecto
    from modules.memorias.models.memorias import Memoria
    from modules.memorias.services.memoria_service import MemoriaService
    from modules.personal.models.identidad import IdentidadPersonal
    from modules.personal.models.personal import (Investigador, Becario, Personal, TipoDedicacion, TipoFormacion,
        InvestigadorHorasHistorial, BecarioHorasHistorial, PersonalHorasHistorial)
    from modules.personal.models.tipo_personal import TipoPersonal
    from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, TipoProyecto
    from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
    from modules.produccion.models.actividad_docencia import ActividadDocencia
    from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
    from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica, TipoReunion
    from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato, TipoRevista
    from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor
    from modules.recursos.models.equipamiento import Equipamiento
    from modules.recursos.models.becas import Beca, Beca_Becario
    from modules.recursos.models.movimiento_financiero import CategoriaErogacion, MovimientoFinanciero
    from modules.transferencia.models.transferencia_socio import (TransferenciaSocioProductiva, TipoContrato, Adoptante, AdoptanteTransferencia)

    if current_app.config["APP_ENV"] != "testing":
        raise RuntimeError("Esta seed requiere APP_ENV=testing y una base dedicada")
    user = db.session.get(Usuario, user_id)
    if user is None or not user.activo or user.deleted_at is not None or user.rol.nombre != "ADMIN":
        raise ValueError("Seleccione un usuario ADMIN activo para registrar la auditoría")
    data = dataset or read_dataset()
    existing_group = GrupoInvestigacionUtn.query.filter_by(nombre_sigla_grupo=data["grupo"]["nombre_sigla_grupo"]).first()
    if existing_group:
        memoria = Memoria.query.filter_by(grupo_utn_id=existing_group.id, periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31)).first()
        if memoria and memoria.deleted_at is None:
            return {"grupo_id": existing_group.id, "memoria_id": memoria.id, "created": False}
        raise RuntimeError("La UCT ya existe sin la memoria esperada; no se sobrescribe una carga ajena")
    if GrupoInvestigacionUtn.query.first():
        raise RuntimeError("La seed requiere una base dedicada sin otras UCT")

    def add(model, **values):
        if hasattr(model, "created_by"):
            values["created_by"] = user_id
        item = model(**values)
        db.session.add(item)
        db.session.flush()
        return item

    def catalog(model, name):
        name = text(name) or "Sin especificar"
        return model.query.filter_by(nombre=name).first() or add(model, nombre=name)

    identities = {}
    investigators = {}
    scholars = {}
    warnings = []

    def identity(name):
        key = name_key(name)
        if key not in identities:
            dni = str(88000001 + len(identities))
            base = "20" + dni
            digit = 11 - sum(int(c) * w for c, w in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
            digit = 0 if digit == 11 else 9 if digit == 10 else digit
            identities[key] = add(IdentidadPersonal, dni=dni, cuil=f"20-{dni}-{digit}")
        return identities[key]

    try:
        grupo = add(GrupoInvestigacionUtn, **data["grupo"])
        add(UsuarioGrupoUtn, usuario_id=user_id, grupo_utn_id=grupo.id)
        for item in data["directivos"]:
            directivo = add(Directivo, nombre_apellido=item["nombre_apellido"], grupo_utn_id=grupo.id)
            add(DirectivoGrupo, id_directivo=directivo.id, id_grupo_utn=grupo.id,
                id_cargo=catalog(Cargo, item["cargo"]).id, fecha_inicio=date(2025, 1, 1))

        def investigator(name, hours=10, categoria=None, incentivos=None, dedicacion="Ad-honorem"):
            key = name_key(name)
            if key not in investigators:
                inv = add(Investigador, nombre_apellido=text(name), identidad=identity(name), horas_semanales=int(hours),
                    fecha_alta_grupo=date(2025, 1, 1), grupo_utn_id=grupo.id,
                    tipo_dedicacion_id=catalog(TipoDedicacion, dedicacion).id,
                    categoria_utn_id=catalog(CategoriaUtn, categoria).id if categoria not in (None, "", "-") else None,
                    programa_incentivos_id=catalog(ProgramaIncentivos, incentivos).id if incentivos not in (None, "", "-") else None)
                add(InvestigadorHorasHistorial, investigador_id=inv.id, horas_semanales=inv.horas_semanales, fecha_inicio=date(2025, 1, 1))
                investigators[key] = inv
            return investigators[key]

        for item in data["investigadores"]:
            investigator(item["nombre_apellido"], item["horas"], item["categoria"], item["incentivos"], item["dedicacion"])
        for item in data["personal"]:
            name = text(item["nombre_apellido"]).split("(", 1)[0].strip()
            person = add(Personal, nombre_apellido=name, identidad=identity(name), horas_semanales=int(item["horas"]),
                fecha_alta_grupo=date(2025, 1, 1), grupo_utn_id=grupo.id, tipo_personal_id=catalog(TipoPersonal, "Profesional").id)
            add(PersonalHorasHistorial, personal_id=person.id, horas_semanales=person.horas_semanales, fecha_inicio=date(2025, 1, 1))

        for item in data["becarios"]:
            key = name_key(item["nombre_apellido"])
            becario = scholars.get(key)
            if becario is None:
                becario = add(Becario, nombre_apellido=text(item["nombre_apellido"]), identidad=identity(item["nombre_apellido"]),
                    horas_semanales=int(item["horas"] or 10), fecha_alta_grupo=date(2025, 1, 1),
                    grupo_utn_id=grupo.id, tipo_formacion_id=catalog(TipoFormacion, item["categoria"]).id)
                add(BecarioHorasHistorial, becario_id=becario.id, horas_semanales=becario.horas_semanales, fecha_inicio=date(2025, 1, 1))
                scholars[key] = becario
            elif becario.tipo_formacion.nombre != item["categoria"]:
                warnings.append(f"Fila {item['source_row']}: {becario.nombre_apellido} tiene más de una formación; el modelo conserva una sola.")
            source = text(item["fuente"])
            if source and source != "-":
                fuente = catalog(FuenteFinanciamiento, source)
                beca = Beca.query.filter_by(grupo_utn_id=grupo.id, nombre_beca=source).first()
                if beca is None:
                    beca = add(Beca, grupo_utn_id=grupo.id, nombre_beca=source, descripcion=source,
                        fecha_alta_grupo=date(2025, 1, 1), fuente_financiamiento_id=fuente.id)
                if not Beca_Becario.query.filter_by(id_beca=beca.id, id_becario=becario.id).first():
                    add(Beca_Becario, id_beca=beca.id, id_becario=becario.id, fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 12, 31))

        for item in data["equipamiento"]:
            add(Equipamiento, denominacion=text(item["denominacion"]), descripcion_breve=text(item["descripcion"]) or text(item["denominacion"]),
                fecha_incorporacion=first_date(item["fecha"]), monto_invertido=float(amount(item["monto"])), grupo_utn_id=grupo.id)
        projects = []
        for index, item in enumerate(data["proyectos"], 1):
            dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", text(item["periodo"]))
            project = add(ProyectoInvestigacion, codigo_proyecto=text(item["codigo"])[:50] or f"EXT-2025-{index}",
                nombre_proyecto=text(item["nombre"]), descripcion_proyecto=text(item["descripcion"]),
                dificultades_proyecto=text(item["dificultades"]), fecha_inicio=first_date(item["periodo"]),
                fecha_fin=first_date(dates[-1]) if len(dates) > 1 else date(2026, 12, 31),
                monto_destinado=float(amount(item["monto"])), grupo_utn_id=grupo.id,
                tipo_proyecto_id=catalog(TipoProyecto, item["tipo"]).id, fuente_financiamiento_id=catalog(FuenteFinanciamiento, item["fuente"] or "UTN").id)
            projects.append((project, item))

        for item in data["docencia"]:
            inv = investigator(text(item["nombre_apellido"]).replace("\xa0", ""))
            add(ActividadDocencia, investigador_id=inv.id, curso=text(item["curso"]), institucion="UTN - Facultad Regional La Plata" if "Universidad Nacional de La Plata" not in text(item["curso"]) else "Universidad Nacional de La Plata",
                fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 12, 31))
        default_inv = next(iter(investigators.values()))
        for item in data["participaciones"]:
            add(ParticipacionRelevante, nombre_evento=item["descripcion"], forma_participacion="Participación institucional",
                fecha=first_date(item["descripcion"]), investigador_id=default_inv.id)
        for item in data["articulos"]:
            add(ArticuloDivulgacion, titulo=item["descripcion"], descripcion=item["descripcion"], fecha_publicacion=date(2025, 12, 1), grupo_utn_id=grupo.id)

        for item in data["reuniones"]:
            work = add(TrabajoReunionCientifica, titulo_trabajo=text(item["titulo"]), nombre_reunion=text(item["nombre_reunion"]),
                procedencia=text(item["procedencia"]), fecha_presentacion=first_date(item["fecha"]), grupo_utn_id=grupo.id,
                tipo_reunion_id=catalog(TipoReunion, item["tipo"]).id)
            # Autores externos también necesitan un integrante para cumplir el contrato actual.
            names = re.split(r";|\n", text(item["expositores"]))
            for name in names:
                if name.strip():
                    key = name_key(name)
                    becario = scholars.get(key)
                    inv = None if becario else investigator(name)
                    if not TrabajoReunionAutor.query.filter_by(trabajo_id=work.id, **({"becario_id": becario.id} if becario else {"investigador_id": inv.id})).first():
                        db.session.add(TrabajoReunionAutor(trabajo_id=work.id, becario_id=becario.id if becario else None, investigador_id=inv.id if inv else None))
        for item in data["revistas"]:
            work = add(TrabajosRevistasReferato, titulo_trabajo=text(item["titulo"]), nombre_revista=text(item["nombre_revista"]),
                editorial=text(item["editorial"]), issn=text(item["issn"]), pais=text(item["pais"]), fecha_publicacion=date(2025, 12, 1),
                grupo_utn_id=grupo.id, tipo_revista_id=catalog(TipoRevista, "Con referato").id)
            db.session.add(TrabajoRevistaAutor(trabajo_id=work.id, investigador_id=default_inv.id))
        for index, item in enumerate(data["transferencias"], 1):
            transferencia = add(TransferenciaSocioProductiva, numero_transferencia=index, denominacion=text(item["denominacion"]),
                demandante=text(item["demandante"]) or text(item["adoptante"]) or "Comunidad académica",
                descripcion_actividad=text(item["descripcion"]) if item["descripcion"] not in (None, "", "-") else text(item["denominacion"]),
                monto=float(amount(item["monto"])), fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 12, 31),
                grupo_utn_id=grupo.id, tipo_contrato_id=catalog(TipoContrato, item["tipo"]).id)
            adoptante = add(Adoptante, nombre=text(item["adoptante"]) or "Comunidad académica", grupo_utn_id=grupo.id)
            add(AdoptanteTransferencia, transferencia_id=transferencia.id, adoptante_id=adoptante.id)

        corriente = CategoriaErogacion.query.filter_by(codigo="CORRIENTE").first() or add(CategoriaErogacion, codigo="CORRIENTE", nombre="Corriente")
        number = 0
        for item in data["finanzas"]:
            source = catalog(FuenteFinanciamiento, item["fuente"])
            for tipo, field in (("INGRESO", "ingresos"), ("EGRESO", "egresos")):
                value = amount(item[field])
                if value > 0:
                    number += 1
                    add(MovimientoFinanciero, grupo_utn_id=grupo.id, numero_movimiento=number, fecha=date(2025, 12, 15), tipo_movimiento=tipo,
                        monto=value, moneda="ARS", monto_equivalente_ars=value, fuente_financiamiento_id=source.id,
                        categoria_erogacion_id=corriente.id if tipo == "EGRESO" else None)
        add(PlanificacionGrupo, descripcion=data["programa_actividades"], anio=2026, grupo_id=grupo.id)
        memoria = add(Memoria, grupo_utn_id=grupo.id, periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31))
        MemoriaService._crear_version_inicial(memoria, user_id, datetime(2025, 1, 1))
        for project, item in projects:
            report = add(Informe, tipo="pid", memoria_id=memoria.id, grupo_utn_id=grupo.id,
                titulo=project.codigo_proyecto, fecha_realizacion=date(2025, 12, 31), resumen=project.descripcion_proyecto,
                actividades=project.descripcion_proyecto, resultados=text(item["logros"]) or "No se registraron resultados en el período.",
                observaciones=project.dificultades_proyecto or "Sin observaciones.", uct_snapshot={"nombre": grupo.nombre_sigla_grupo})
            add(InformeProyecto, informe_id=report.id, proyecto_id=project.id, snapshot={"nombre_proyecto": project.nombre_proyecto})
        add(Informe, tipo="uct", memoria_id=memoria.id, grupo_utn_id=grupo.id, titulo="Memoria institucional 2025",
            fecha_realizacion=date(2025, 12, 31), resumen=grupo.objetivo_desarrollo, actividades=data["organigrama"],
            resultados="\n\n".join(item["descripcion"] for item in data["participaciones"]), observaciones="Sin observaciones.",
            uct_snapshot={"nombre": grupo.nombre_sigla_grupo})
        db.session.commit()
        return {"grupo_id": grupo.id, "memoria_id": memoria.id, "version_id": memoria.version_actual_id,
                "created": True, "limitaciones": warnings}
    except Exception:
        db.session.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--close", action="store_true")
    parser.add_argument("--initialize", action="store_true", help="Crear esquema y usuarios en una base dedicada vacía")
    parser.add_argument("--output", type=Path, help="Guardar el Excel generado desde la versión cerrada")
    parser.add_argument("--scenario-2026", action="store_true", help="Poblar GIDAS para validación manual, sin crear memoria ni Excel")
    parser.add_argument("--group-id", type=int)
    parser.add_argument("--replace-2026", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.scenario_2026:
        if not args.group_id or not args.user_id or args.close or args.output or args.initialize:
            parser.error("El escenario 2026 requiere --group-id y --user-id; no admite --close, --output ni --initialize")
        from app import app
        from tools.seed_memoria_validacion import populate
        with app.app_context():
            result = populate(args.group_id, args.user_id, replace=args.replace_2026, dry_run=not args.apply)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output, encoding="utf-8")
        print(output)
        return
    data = read_dataset(args.source)
    if not args.apply:
        print(json.dumps({key: len(value) for key, value in data.items() if isinstance(value, list)}, ensure_ascii=False, indent=2))
        return
    if os.getenv("APP_ENV") != "testing" or not (args.user_id or args.initialize):
        parser.error("Para cargar: APP_ENV=testing, base dedicada y --user-id de un ADMIN activo")
    if args.output and args.output.resolve() == args.source.resolve():
        parser.error("El archivo generado debe ser distinto del documento de referencia")
    if args.initialize and len(os.getenv("SEED_ADMIN_PASSWORD", "")) < 12:
        parser.error("--initialize requiere SEED_ADMIN_PASSWORD de al menos 12 caracteres")
    from app import app
    from modules.memorias.services.memoria_service import MemoriaService
    with app.app_context():
        from extension import db
        bootstrap_users = []
        if args.initialize:
            from modules.auth.models.usuario import RolUsuario, Usuario
            from modules.auth.models.persona import Persona
            db.create_all()
            if Usuario.query.first():
                parser.error("--initialize requiere una base sin usuarios; para repetir la seed use --user-id")
            for index, (nombre, rol_nombre) in enumerate((("admin", "ADMIN"), ("gestor", "GESTOR"), ("lector", "LECTURA")), 1):
                rol = RolUsuario.query.filter_by(nombre=rol_nombre).first()
                if rol is None:
                    rol = RolUsuario(nombre=rol_nombre)
                    db.session.add(rol)
                    db.session.flush()
                persona = Persona(nombre_apellido=nombre.capitalize(), dni=87990000 + index)
                db.session.add(persona)
                db.session.flush()
                usuario = Usuario(nombre_usuario=nombre, mail=f"{nombre}@gidas.local", id_persona=persona.id, id_rol=rol.id, primer_login=False)
                usuario.set_password(os.environ["SEED_ADMIN_PASSWORD"])
                db.session.add(usuario)
                db.session.flush()
                bootstrap_users.append(usuario.id)
            args.user_id = bootstrap_users[0]
            db.session.commit()
        result = seed_memoria_2025(args.user_id, data)
        if bootstrap_users:
            from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
            for usuario_id in bootstrap_users[1:]:
                db.session.add(UsuarioGrupoUtn(usuario_id=usuario_id, grupo_utn_id=result["grupo_id"], created_by=args.user_id))
            db.session.commit()
        if args.close:
            from modules.memorias.models.memorias import Memoria, EstadoMemoria
            memoria = db.session.get(Memoria, result["memoria_id"])
            if memoria.version_actual.estado != EstadoMemoria.CERRADA:
                MemoriaService.change_status(memoria.id, {"estado": "cerrada"}, args.user_id)
        if args.output:
            from modules.memorias.services.exportacion_service_impl import ExportService
            from modules.memorias.models.memorias import Memoria
            memoria = db.session.get(Memoria, result["memoria_id"])
            content = ExportService.generar_excel_memoria(memoria.id, memoria.version_actual_id)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(content.getvalue())
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
