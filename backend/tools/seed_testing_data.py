import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import app
from extension import db
from modules.catalogos.models.categoria_utn import CategoriaUtn
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.grupo.models.directivos import Cargo, Directivo, DirectivoGrupo
from modules.grupo.models.visita_grupo import TipoVisita, VisitaAcademica
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.auth.models.persona import Persona
from modules.personal.models.personal import (
    Becario,
    BecarioHorasHistorial,
    Investigador,
    InvestigadorHorasHistorial,
    Personal,
    PersonalHorasHistorial,
    TipoDedicacion,
    TipoFormacion,
)
from modules.grupo.models.programa_incentivos import ProgramaIncentivos
from modules.proyectos.models.proyecto_investigacion import (
    BecarioProyecto,
    InvestigadorProyecto,
    ProyectoInvestigacion,
    TipoProyecto,
)
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.models.identidad import IdentidadPersonal
from modules.produccion.models.actividad_docencia import ActividadDocencia
from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
from modules.produccion.models.documentacion_autores import (
    Autor,
    DocumentacionBibliografica,
)
from modules.produccion.models.registro_patente import (
    RegistrosPropiedad,
    TipoRegistroPropiedad,
)
from modules.produccion.models.trabajo_reunion import TipoReunion, TrabajoReunionCientifica
from modules.produccion.models.trabajo_revista import TipoRevista, TrabajosRevistasReferato
from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
from modules.recursos.models.becas import Beca
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.models.movimiento_financiero import CategoriaErogacion, MovimientoFinanciero
from modules.transferencia.models.transferencia_socio import (
    TipoContrato,
    TransferenciaSocioProductiva,
)
from modules.auth.models.usuario import RolUsuario, Usuario


TEST_PASSWORD = "Testing123!"
MANUAL_VARIANT_COUNT = 12


def _ensure_testing_identity(entity, dni_number):
    """Completa identidades ficticias de forma repetible."""
    if entity.identidad:
        return
    dni = str(dni_number)
    base = f"20{dni}"
    remainder = 11 - sum(int(digit) * weight for digit, weight in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
    check = 0 if remainder == 11 else 9 if remainder == 10 else remainder
    entity.identidad = IdentidadPersonal(dni=dni, cuil=f"20-{dni}-{check}")


def _assert_testing_environment():
    app_env = os.getenv("APP_ENV", "").strip().lower()
    allow_seed = os.getenv("ALLOW_TEST_SEED", "").strip().lower() == "true"
    if app_env != "testing" and not allow_seed:
        raise RuntimeError(
            "Seed cancelado: requiere APP_ENV=testing o ALLOW_TEST_SEED=true"
        )


def _get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance, False

    values = {**filters, **(defaults or {})}
    instance = model(**values)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def _seed_roles():
    roles = {}
    for nombre in ["ADMIN", "GESTOR", "LECTURA"]:
        rol, _ = _get_or_create(RolUsuario, nombre=nombre)
        roles[nombre] = rol
    return roles


def _seed_user(nombre_usuario, mail, nombre_apellido, dni, rol):
    user = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
    if user:
        return user

    persona, _ = _get_or_create(
        Persona,
        dni=dni,
        defaults={"nombre_apellido": nombre_apellido},
    )
    user = Usuario(
        nombre_usuario=nombre_usuario,
        mail=mail,
        id_rol=rol.id,
        id_persona=persona.id,
        primer_login=False,
    )
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


def _seed_catalogs():
    categoria, _ = _get_or_create(CategoriaUtn, nombre="Investigador formado")
    dedicacion, _ = _get_or_create(TipoDedicacion, nombre="Exclusiva")
    programa, _ = _get_or_create(ProgramaIncentivos, nombre="Categoria III")
    tipo_formacion, _ = _get_or_create(TipoFormacion, nombre="Beca doctoral")
    tipo_personal, _ = _get_or_create(
        TipoPersonal,
        nombre="Técnico administrativo y de apoyo",
    )
    tipo_profesional, _ = _get_or_create(TipoPersonal, nombre="Profesional")
    tipo_proyecto, _ = _get_or_create(TipoProyecto, nombre="I+D")
    fuente, _ = _get_or_create(FuenteFinanciamiento, nombre="UTN")
    tipo_visita_academica, _ = _get_or_create(TipoVisita, nombre="Académica")
    tipo_visita_intercambio, _ = _get_or_create(TipoVisita, nombre="Intercambio")
    return {
        "categoria": categoria,
        "dedicacion": dedicacion,
        "programa": programa,
        "tipo_formacion": tipo_formacion,
        "tipo_personal": tipo_personal,
        "tipo_profesional": tipo_profesional,
        "tipo_proyecto": tipo_proyecto,
        "fuente": fuente,
        "tipo_visita_academica": tipo_visita_academica,
        "tipo_visita_intercambio": tipo_visita_intercambio,
    }


def _seed_group():
    # La aplicación muestra una única UCT activa. Usar esa misma UCT evita
    # generar movimientos buscables que no aparecen en su historial financiero.
    grupo = GrupoInvestigacionUtn.query.filter(
        GrupoInvestigacionUtn.deleted_at.is_(None)
    ).order_by(GrupoInvestigacionUtn.id.asc()).first()
    if grupo:
        return grupo

    grupo = GrupoInvestigacionUtn(
        mail="gidas.testing@example.com",
        nombre_unidad_academica="Facultad Regional de Prueba",
        objetivo_desarrollo="Datos ficticios para validar flujos del sistema.",
        nombre_sigla_grupo="GIDAS TEST",
    )
    db.session.add(grupo)
    db.session.flush()
    return grupo


def _seed_people(grupo, catalogs, admin_user_id):
    investigador, _ = _get_or_create(
        Investigador,
        nombre_apellido="Dra. Ana Perez",
        defaults={
            "horas_semanales": 40,
            "fecha_alta_grupo": date(2024, 1, 1),
            "tipo_dedicacion_id": catalogs["dedicacion"].id,
            "categoria_utn_id": catalogs["categoria"].id,
            "programa_incentivos_id": catalogs["programa"].id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _ensure_testing_identity(investigador, 90000001)
    if not investigador.historial_horas:
        db.session.add(
            InvestigadorHorasHistorial(
                investigador=investigador,
                horas_semanales=40,
                fecha_inicio=date(2024, 1, 1),
                created_by=admin_user_id,
            )
        )

    becario, _ = _get_or_create(
        Becario,
        nombre_apellido="Lic. Bruno Gomez",
        defaults={
            "horas_semanales": 20,
            "fecha_alta_grupo": date(2024, 3, 1),
            "tipo_formacion_id": catalogs["tipo_formacion"].id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _ensure_testing_identity(becario, 90000002)
    if not becario.historial_horas:
        db.session.add(
            BecarioHorasHistorial(
                becario=becario,
                horas_semanales=20,
                fecha_inicio=date(2024, 3, 1),
                created_by=admin_user_id,
            )
        )

    personal, _ = _get_or_create(
        Personal,
        nombre_apellido="Carla Ruiz",
        defaults={
            "horas_semanales": 30,
            "fecha_alta_grupo": date(2024, 2, 1),
            "tipo_personal_id": catalogs["tipo_personal"].id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _ensure_testing_identity(personal, 90000003)
    if not personal.historial_horas:
        db.session.add(
            PersonalHorasHistorial(
                personal=personal,
                horas_semanales=30,
                fecha_inicio=date(2024, 2, 1),
                created_by=admin_user_id,
            )
        )

    return investigador, becario, personal


def _seed_manual_people(grupo, catalogs, admin_user_id):
    """Crea personal variado de las cuatro categorias visibles en la UI."""
    for index in range(1, MANUAL_VARIANT_COUNT + 1):
        year = 2022 + ((index - 1) % 4)
        month = ((index - 1) % 12) + 1
        hours = [10, 20, 30, 40][(index - 1) % 4]
        suffix = f"{index:02d} TEST"

        for prefix, tipo_personal in [
            ("Tecnico Administrativo", catalogs["tipo_personal"]),
            ("Profesional", catalogs["tipo_profesional"]),
        ]:
            person, _ = _get_or_create(
                Personal,
                nombre_apellido=f"{prefix} {suffix}",
                defaults={
                    "horas_semanales": hours,
                    "fecha_alta_grupo": date(year, month, 1),
                    "tipo_personal_id": tipo_personal.id,
                    "grupo_utn_id": grupo.id,
                    "created_by": admin_user_id,
                },
            )
            _ensure_testing_identity(person, 90001000 + index * 4 + (0 if prefix.startswith("Tecnico") else 1))
            if not person.historial_horas:
                db.session.add(
                    PersonalHorasHistorial(
                        personal=person,
                        horas_semanales=hours,
                        fecha_inicio=date(year, month, 1),
                        created_by=admin_user_id,
                    )
                )

        becario, _ = _get_or_create(
            Becario,
            nombre_apellido=f"Becario {suffix}",
            defaults={
                "horas_semanales": hours,
                "fecha_alta_grupo": date(year, month, 2),
                "tipo_formacion_id": catalogs["tipo_formacion"].id,
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )
        _ensure_testing_identity(becario, 90001000 + index * 4 + 2)
        if not becario.historial_horas:
            db.session.add(
                BecarioHorasHistorial(
                    becario=becario,
                    horas_semanales=hours,
                    fecha_inicio=date(year, month, 2),
                    created_by=admin_user_id,
                )
            )

        investigador, _ = _get_or_create(
            Investigador,
            nombre_apellido=f"Investigador {suffix}",
            defaults={
                "horas_semanales": hours,
                "fecha_alta_grupo": date(year, month, 3),
                "tipo_dedicacion_id": catalogs["dedicacion"].id,
                "categoria_utn_id": catalogs["categoria"].id,
                "programa_incentivos_id": catalogs["programa"].id,
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )
        _ensure_testing_identity(investigador, 90001000 + index * 4 + 3)
        if not investigador.historial_horas:
            db.session.add(
                InvestigadorHorasHistorial(
                    investigador=investigador,
                    horas_semanales=hours,
                    fecha_inicio=date(year, month, 3),
                    created_by=admin_user_id,
                )
            )


def _seed_project(grupo, catalogs, investigador, becario, admin_user_id):
    proyecto = ProyectoInvestigacion.query.filter_by(
        codigo_proyecto="2026001"
    ).first()
    if not proyecto:
        proyecto = ProyectoInvestigacion(
            codigo_proyecto="2026001",
            nombre_proyecto="Plataforma de gestion academica de prueba",
            descripcion_proyecto="Proyecto ficticio para operar el entorno testing.",
            fecha_inicio=date(2024, 1, 1),
            fecha_fin=None,
            dificultades_proyecto="Sin dificultades registradas.",
            monto_destinado=1500000,
            tipo_proyecto_id=catalogs["tipo_proyecto"].id,
            grupo_utn_id=grupo.id,
            fuente_financiamiento_id=catalogs["fuente"].id,
            created_by=admin_user_id,
        )
        db.session.add(proyecto)
        db.session.flush()

    if not InvestigadorProyecto.query.filter_by(
        id_investigador=investigador.id,
        id_proyecto=proyecto.id,
    ).first():
        db.session.add(
            InvestigadorProyecto(
                investigador=investigador,
                proyecto=proyecto,
                es_coordinador=True,
                fecha_inicio=date(2024, 1, 1),
                created_by=admin_user_id,
            )
        )

    if not BecarioProyecto.query.filter_by(
        id_becario=becario.id,
        id_proyecto=proyecto.id,
    ).first():
        db.session.add(
            BecarioProyecto(
                becario=becario,
                proyecto=proyecto,
                fecha_inicio=date(2024, 3, 1),
                created_by=admin_user_id,
            )
        )


def _seed_memoria(admin_user_id):
    memoria = Memoria.query.filter_by(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    ).first()
    if memoria:
        return memoria

    memoria = Memoria(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
        created_by=admin_user_id,
    )
    db.session.add(memoria)
    db.session.flush()

    version = MemoriaVersion(
        memoria_id=memoria.id,
        numero_version=1,
        fecha_apertura=datetime.utcnow(),
        estado=EstadoMemoria.ABIERTA,
        created_by=admin_user_id,
    )
    db.session.add(version)
    db.session.flush()

    memoria.version_actual_id = version.id
    return memoria


def _seed_search_coverage(grupo, catalogs, investigador, admin_user_id):
    categoria_erogacion, _ = _get_or_create(
        CategoriaErogacion, codigo="CORRIENTE",
        defaults={"nombre": "Corriente"},
    )
    tipo_registro, _ = _get_or_create(
        TipoRegistroPropiedad,
        nombre="Patente experimental TEST",
    )
    tipo_contrato, _ = _get_or_create(
        TipoContrato,
        nombre="Convenio de asistencia TEST",
    )
    tipo_reunion, _ = _get_or_create(TipoReunion, nombre="Jornada academica TEST")
    tipo_revista, _ = _get_or_create(TipoRevista, nombre="Nacional")
    _get_or_create(TipoRevista, nombre="Internacional")

    _get_or_create(
        Beca,
        nombre_beca="Beca de investigacion TEST",
        defaults={
            "descripcion": "Registro ficticio para validar la busqueda.",
            "fecha_alta_grupo": date(2024, 4, 1),
            "fuente_financiamiento_id": catalogs["fuente"].id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        ActividadDocencia,
        curso="Seminario de datos TEST",
        investigador_id=investigador.id,
        defaults={
            "institucion": "Universidad de Prueba",
            "fecha_inicio": date(2024, 5, 1),
            "fecha_fin": date(2024, 5, 31),
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        Equipamiento,
        denominacion="Microscopio digital TEST",
        grupo_utn_id=grupo.id,
        defaults={
            "descripcion_breve": "Equipo ficticio para validar recuperacion.",
            "fecha_incorporacion": date(2024, 2, 15),
            "monto_invertido": 125000.0,
            "created_by": admin_user_id,
        },
    )

    autor, _ = _get_or_create(Autor, nombre_apellido="Autora Ficticia TEST")
    documento, _ = _get_or_create(
        DocumentacionBibliografica,
        titulo="Manual de investigacion TEST",
        grupo_id=grupo.id,
        defaults={
            "editorial": "Editorial de Prueba",
            "anio": 2024,
            "fecha": date(2024, 6, 1),
            "created_by": admin_user_id,
        },
    )
    if autor not in documento.autores:
        documento.autores.append(autor)

    _get_or_create(
        MovimientoFinanciero,
        numero_movimiento=990001,
        grupo_utn_id=grupo.id,
        defaults={
            "tipo_movimiento": "INGRESO",
            "monto": "50000.00",
            "moneda": "ARS",
            "fecha": date(2024, 6, 15),
            "fuente_financiamiento_id": catalogs["fuente"].id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        MovimientoFinanciero,
        numero_movimiento=990002,
        grupo_utn_id=grupo.id,
        defaults={
            "tipo_movimiento": "EGRESO",
            "monto": "25000.00",
            "moneda": "ARS",
            "fecha": date(2024, 6, 15),
            "fuente_financiamiento_id": catalogs["fuente"].id,
            "categoria_erogacion_id": categoria_erogacion.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        ParticipacionRelevante,
        nombre_evento="Congreso de tecnologia TEST",
        defaults={
            "forma_participacion": "Expositor ficticio",
            "fecha": date(2024, 7, 10),
            "investigador_id": investigador.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        RegistrosPropiedad,
        nombre_articulo="Dispositivo experimental TEST",
        grupo_utn_id=grupo.id,
        defaults={
            "organismo_registrante": "Organismo de Prueba",
            "fecha_registro": date(2024, 8, 1),
            "tipo_registro_id": tipo_registro.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        TransferenciaSocioProductiva,
        numero_transferencia=990001,
        defaults={
            "denominacion": "Transferencia tecnologica TEST",
            "demandante": "Empresa Ficticia",
            "descripcion_actividad": "Asistencia tecnica integral TEST",
            "monto": 50000.0,
            "fecha_inicio": date(2024, 8, 15),
            "tipo_contrato_id": tipo_contrato.id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        TrabajoReunionCientifica,
        titulo_trabajo="Resultados de laboratorio TEST",
        defaults={
            "nombre_reunion": "Jornada Ficticia",
            "procedencia": "Universidad de Prueba",
            "fecha_presentacion": date(2024, 9, 1),
            "tipo_reunion_id": tipo_reunion.id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        TrabajosRevistasReferato,
        titulo_trabajo="Articulo con referato TEST",
        defaults={
            "nombre_revista": "Revista Ficticia",
            "editorial": "Editorial de Prueba",
            "issn": "0000-0000",
            "pais": "Argentina",
            "fecha_publicacion": date(2024, 9, 15),
            "grupo_utn_id": grupo.id,
            "tipo_revista_id": tipo_revista.id,
            "created_by": admin_user_id,
        },
    )
    directivo, _ = _get_or_create(
        Directivo,
        nombre_apellido="Directiva Ficticia TEST",
        defaults={"created_by": admin_user_id},
    )
    cargo, _ = _get_or_create(Cargo, nombre="Director")
    _get_or_create(
        DirectivoGrupo,
        id_directivo=directivo.id,
        id_grupo_utn=grupo.id,
        defaults={
            "id_cargo": cargo.id,
            "fecha_inicio": date(2024, 1, 1),
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        ArticuloDivulgacion,
        titulo="Divulgacion cientifica TEST",
        defaults={
            "descripcion": "Articulo ficticio para validar busqueda.",
            "fecha_publicacion": date(2024, 10, 1),
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )
    _get_or_create(
        VisitaAcademica,
        razon="Intercambio academico TEST",
        defaults={
            "fecha": date(2024, 10, 15),
            "procedencia": "Instituto de Prueba",
            "tipo_visita_id": catalogs["tipo_visita_intercambio"].id,
            "grupo_utn_id": grupo.id,
            "created_by": admin_user_id,
        },
    )


def _seed_manual_testing_dataset(grupo, catalogs, investigador, admin_user_id):
    """Crea variantes deterministas para probar filtros y paginacion manual."""
    categorias_erogacion = [
        _get_or_create(CategoriaErogacion, codigo=codigo,
                       defaults={"nombre": nombre})[0]
        for codigo, nombre in [("CORRIENTE", "Corriente"), ("CAPITAL", "Capital")]
    ]
    tipos_registro = [
        _get_or_create(TipoRegistroPropiedad, nombre=nombre)[0]
        for nombre in [
            "Patente TEST",
            "Modelo de utilidad TEST",
            "Software TEST",
        ]
    ]
    tipos_contrato = [
        _get_or_create(TipoContrato, nombre=nombre)[0]
        for nombre in [
            "Asistencia tecnica TEST",
            "Licencia TEST",
            "Convenio TEST",
        ]
    ]
    tipos_reunion = [
        _get_or_create(TipoReunion, nombre=nombre)[0]
        for nombre in [
            "Congreso TEST",
            "Jornada TEST",
            "Seminario TEST",
        ]
    ]
    tipos_visita = [
        catalogs["tipo_visita_academica"],
        catalogs["tipo_visita_intercambio"],
    ]
    tipos_revista = [
        _get_or_create(TipoRevista, nombre=nombre)[0]
        for nombre in ["Nacional", "Internacional"]
    ]

    instituciones = [
        "Universidad Regional Norte",
        "Instituto Tecnologico Centro",
        "Facultad Regional Sur",
    ]
    paises = ["Argentina", "Uruguay", "Chile"]
    demandantes = ["Cooperativa Alfa", "Municipalidad Beta", "PyME Gamma"]

    for index in range(1, MANUAL_VARIANT_COUNT + 1):
        year = 2022 + ((index - 1) % 4)
        month = ((index - 1) % 12) + 1
        variant = f"{index:02d} TEST"
        tipo_index = (index - 1) % 3

        _get_or_create(
            Beca,
            nombre_beca=f"Beca {variant}",
            defaults={
                "descripcion": f"Beca ficticia de la cohorte {year} para pruebas manuales.",
                "fecha_alta_grupo": date(year, month, 1),
                "fuente_financiamiento_id": catalogs["fuente"].id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            ActividadDocencia,
            curso=f"Curso de innovacion {variant}",
            investigador_id=investigador.id,
            defaults={
                "institucion": instituciones[tipo_index],
                "fecha_inicio": date(year, month, 1),
                "fecha_fin": date(year, month, min(20 + tipo_index, 28)),
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            Equipamiento,
            denominacion=f"Equipo de laboratorio {variant}",
            grupo_utn_id=grupo.id,
            defaults={
                "descripcion_breve": f"Equipamiento ficticio categoria {tipo_index + 1}.",
                "fecha_incorporacion": date(year, month, 10),
                "monto_invertido": 50000.0 + index * 17500.0,
                "created_by": admin_user_id,
            },
        )

        autor, _ = _get_or_create(
            Autor,
            nombre_apellido=f"Autor Ficticio {variant}",
        )
        documento, _ = _get_or_create(
            DocumentacionBibliografica,
            titulo=f"Publicacion tecnica {variant}",
            grupo_id=grupo.id,
            defaults={
                "editorial": f"Editorial {paises[tipo_index]}",
                "anio": year,
                "fecha": date(year, month, 12),
                "created_by": admin_user_id,
            },
        )
        if autor not in documento.autores:
            documento.autores.append(autor)

        tipo_movimiento = "INGRESO" if index % 2 == 0 else "EGRESO"
        _get_or_create(
            MovimientoFinanciero,
            numero_movimiento=991000 + index,
            grupo_utn_id=grupo.id,
            defaults={
                "tipo_movimiento": tipo_movimiento,
                "monto": str(15000 + index * 3000 if index % 2 == 0 else 10000 + index * 2500),
                "monto_equivalente_ars": str(15000 + index * 3000 if index % 2 == 0 else 10000 + index * 2500),
                "moneda": "ARS",
                "fecha": date(year, month, 15),
                "fuente_financiamiento_id": catalogs["fuente"].id,
                "categoria_erogacion_id": categorias_erogacion[tipo_index % 2].id if tipo_movimiento == "EGRESO" else None,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            ParticipacionRelevante,
            nombre_evento=f"Evento academico {variant}",
            defaults={
                "forma_participacion": ["Expositor", "Organizador", "Asistente"][tipo_index],
                "fecha": date(year, month, 16),
                "investigador_id": investigador.id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            RegistrosPropiedad,
            nombre_articulo=f"Desarrollo registrable {variant}",
            grupo_utn_id=grupo.id,
            defaults={
                "organismo_registrante": instituciones[tipo_index],
                "fecha_registro": date(year, month, 17),
                "tipo_registro_id": tipos_registro[tipo_index].id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            TransferenciaSocioProductiva,
            numero_transferencia=991000 + index,
            defaults={
                "denominacion": f"Transferencia aplicada {variant}",
                "demandante": demandantes[tipo_index],
                "descripcion_actividad": f"Actividad ficticia del sector {tipo_index + 1}.",
                "monto": 25000.0 + index * 12500.0,
                "fecha_inicio": date(year, month, 5),
                "tipo_contrato_id": tipos_contrato[tipo_index].id,
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            TrabajoReunionCientifica,
            titulo_trabajo=f"Ponencia cientifica {variant}",
            defaults={
                "nombre_reunion": f"{tipos_reunion[tipo_index].nombre} {year}",
                "procedencia": instituciones[tipo_index],
                "fecha_presentacion": date(year, month, 18),
                "tipo_reunion_id": tipos_reunion[tipo_index].id,
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            TrabajosRevistasReferato,
            titulo_trabajo=f"Articulo indexado {variant}",
            defaults={
                "nombre_revista": f"Revista {paises[tipo_index]} de Tecnologia",
                "editorial": f"Editorial {tipo_index + 1}",
                "issn": f"{1000 + index:04d}-{2000 + index:04d}",
                "pais": paises[tipo_index],
                "fecha_publicacion": date(year, month, 19),
                "grupo_utn_id": grupo.id,
                "tipo_revista_id": tipos_revista[tipo_index % 2].id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            ArticuloDivulgacion,
            titulo=f"Nota de divulgacion {variant}",
            defaults={
                "descripcion": f"Contenido ficticio sobre la linea {tipo_index + 1}.",
                "fecha_publicacion": date(year, month, 20),
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )
        _get_or_create(
            VisitaAcademica,
            razon=f"Visita por cooperacion {variant}",
            defaults={
                "fecha": date(year, month, 21),
                "procedencia": instituciones[tipo_index],
                "tipo_visita_id": tipos_visita[tipo_index % len(tipos_visita)].id,
                "grupo_utn_id": grupo.id,
                "created_by": admin_user_id,
            },
        )


def seed_testing_data():
    _assert_testing_environment()
    roles = _seed_roles()
    admin = _seed_user(
        "admin.testing",
        "admin.testing@example.com",
        "Admin Testing",
        99000001,
        roles["ADMIN"],
    )
    _seed_user(
        "gestor.testing",
        "gestor.testing@example.com",
        "Gestor Testing",
        99000002,
        roles["GESTOR"],
    )
    _seed_user(
        "lector.testing",
        "lector.testing@example.com",
        "Lector Testing",
        99000003,
        roles["LECTURA"],
    )

    catalogs = _seed_catalogs()
    grupo = _seed_group()
    investigador, becario, personal = _seed_people(grupo, catalogs, admin.id)
    _seed_manual_people(grupo, catalogs, admin.id)
    _seed_project(grupo, catalogs, investigador, becario, admin.id)
    _seed_memoria(admin.id)
    _seed_search_coverage(grupo, catalogs, investigador, admin.id)
    _seed_manual_testing_dataset(grupo, catalogs, investigador, admin.id)

    # ISS-12: dataset mixto e idempotente para ambos tipos de trabajos.
    from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor
    from modules.produccion.services.trabajo_autores_service import sincronizar_autores

    db.session.flush()
    autores = [("investigador", investigador), ("becario", becario)]
    for modelo, asociacion, entidad in (
        (TrabajoReunionCientifica, TrabajoReunionAutor, "trabajo_reunion_cientifica"),
        (TrabajosRevistasReferato, TrabajoRevistaAutor, "trabajo_revista_referato"),
    ):
        for trabajo in modelo.query.filter_by(grupo_utn_id=grupo.id, deleted_at=None).all():
            if not trabajo.autorias:
                sincronizar_autores(trabajo, autores, asociacion, entidad, admin.id)

    db.session.commit()

    print("Datos ficticios de testing cargados correctamente")
    print(
        f"Variantes manuales cargadas: {MANUAL_VARIANT_COUNT} por modulo operativo"
    )
    print("Usuarios de testing cargados; consulte la configuracion local para sus credenciales.")


if __name__ == "__main__":
    with app.app_context():
        seed_testing_data()
