from datetime import datetime
from contextlib import nullcontext
from flask import g, has_app_context, has_request_context, request
from sqlalchemy import func, select, union_all
from sqlalchemy.orm import selectinload

from extension import db
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
from modules.memorias.services.memoria_contexto_service import snapshot_contexto_institucional
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date
from modules.shared.controllers.pagination import paginate_query
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.services.tenant_scope import _classes_by_table
from modules.personal.services.investigador_service import (
    obtener_snapshots_investigadores_por_memoria_version,
    snapshot_investigadores_para_memoria_version,
)
from modules.personal.services.becario_service import (
    snapshot_becarios_para_memoria_version,
    obtener_snapshots_becarios_por_memoria_version,
)
from modules.personal.services.personal_service import (
    snapshot_personal_para_memoria_version,
    obtener_snapshots_personal_por_memoria_version,
)
from modules.proyectos.services.proyecto_investigacion_service import (
    ProyectoInvestigacionService,
)
from modules.produccion.services.actividad_docencia_service import (
    ActividadDocenciaService,
)
from modules.proyectos.services.participacion_relevante_service import (
    ParticipacionRelevanteService,
)
from modules.produccion.services.documentacion_service import (
    DocumentacionBibliograficaService,
)
from modules.recursos.services.equipamiento_service import (
    EquipamientoService,
)
from modules.recursos.services.movimiento_financiero_service import MovimientoFinancieroService
from modules.transferencia.services.transferencia_service import (
    TransferenciaSocioProductivaService,
)
from modules.produccion.services.trabajo_reunion_service import (
    TrabajoReunionCientificaService,
)
from modules.produccion.services.trabajo_revista_service import (
    TrabajosRevistasReferatoService,
)
from modules.produccion.services.distincion_service import (
    DistincionRecibidaService,
)
from modules.produccion.services.registro_propiedad_service import (
    RegistrosPropiedadService,
)
from modules.produccion.services.articulo_divulgacion_service import (
    ArticuloDivulgacionService,
)
from modules.grupo.services.visita_service import (
    obtener_snapshots_visitas_por_memoria_version,
    snapshot_visitas_para_memoria_version,
)


SNAPSHOT_TABLES = (
    "investigador_memoria_version", "becario_memoria_version",
    "personal_memoria_version", "proyecto_investigacion_memoria_version",
    "actividad_docencia_memoria_version", "participacion_relevante_memoria_version",
    "documentacion_bibliografica_memoria_version", "equipamiento_memoria_version",
    "movimiento_memoria_version", "transferencia_socio_productiva_memoria_version",
    "trabajo_reunion_cientifica_memoria_version", "trabajos_revista_memoria_version",
    "distincion_recibida_memoria_version", "registros_propiedad_memoria_version",
    "articulo_divulgacion_memoria_version", "visita_academica_memoria_version",
)

SNAPSHOT_ORDERS = {
    "investigador_memoria_version": (("nombre_apellido", "asc"),),
    "becario_memoria_version": (("nombre_apellido", "asc"),),
    "personal_memoria_version": (("nombre_apellido", "asc"),),
    "proyecto_investigacion_memoria_version": (("nombre_proyecto", "asc"),),
    "actividad_docencia_memoria_version": (("curso", "asc"),),
    "participacion_relevante_memoria_version": (("fecha", "desc"),),
    "documentacion_bibliografica_memoria_version": (("titulo", "asc"),),
    "equipamiento_memoria_version": (("denominacion", "asc"),),
    "movimiento_memoria_version": (("fecha", "desc"), ("numero_movimiento", "desc")),
    "transferencia_socio_productiva_memoria_version": (("fecha_inicio", "desc"),),
    "trabajo_reunion_cientifica_memoria_version": (("fecha_presentacion", "desc"),),
    "trabajos_revista_memoria_version": (("fecha_publicacion", "desc"),),
    "distincion_recibida_memoria_version": (("fecha", "desc"),),
    "registros_propiedad_memoria_version": (("fecha_registro", "desc"),),
    "articulo_divulgacion_memoria_version": (("fecha_publicacion", "desc"),),
    "visita_academica_memoria_version": (("fecha", "desc"),),
}


class MemoriaService:

    @staticmethod
    def _snapshot_page_or_none(version_id: int, table_name: str):
        if not has_request_context() or not pagination_requested(request.args):
            return None
        try:
            params = parse_pagination_params(request.args)
        except ValueError as error:
            raise ValidationError(str(error)) from error

        model = _classes_by_table()[table_name]
        query = model.query.filter(
            model.memoria_version_id == version_id,
            model.deleted_at.is_(None),
        )
        total = query.count()
        order = []
        for column_name, direction in SNAPSHOT_ORDERS[table_name]:
            column = getattr(model, column_name)
            order.append(column.desc() if direction == "desc" else column.asc())
        order.append(model.id.desc() if SNAPSHOT_ORDERS[table_name][0][1] == "desc" else model.id.asc())
        rows = query.order_by(*order).offset(
            (params["page"] - 1) * params["per_page"]
        ).limit(params["per_page"]).all()
        return {
            "data": [row.serialize() for row in rows],
            "meta": {
                "page": params["page"], "per_page": params["per_page"],
                "total": total,
                "total_pages": max(1, (total + params["per_page"] - 1) // params["per_page"]),
                "activos": params["activos"], "orden": params["orden"],
                "source": "legacy-list",
            },
            "error": None,
        }

    # ==========================================
    # HELPERS
    # ==========================================

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or valor <= 0:
            raise ValidationError(f"El campo '{campo}' debe ser un entero positivo")
        return valor

    @staticmethod
    def _validar_texto(valor: str, campo: str):
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError(f"El campo '{campo}' es obligatorio", details={"fields": {campo: "Este campo es obligatorio"}})
        return valor.strip()

    @staticmethod
    def _validar_fecha(fecha_str: str, campo: str):
        valor = MemoriaService._validar_texto(fecha_str, campo)

        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                f"El campo '{campo}' debe tener formato YYYY-MM-DD",
                details={"fields": {campo: "Ingrese una fecha válida en formato YYYY-MM-DD"}},
            )
        try:
            return validate_institutional_date(fecha, campo)
        except ValidationError as error:
            raise ValidationError(str(error), details={"fields": {campo: str(error)}}) from error

    @staticmethod
    def _validar_periodos(periodo_inicio, periodo_fin):
        fecha_inicio = MemoriaService._validar_fecha(
            periodo_inicio, "periodo_inicio"
        )
        fecha_fin = MemoriaService._validar_fecha(
            periodo_fin, "periodo_fin"
        )

        if fecha_inicio > fecha_fin:
            raise ValidationError(
                "La fecha de inicio del periodo no puede ser mayor a la fecha de fin",
                details={"fields": {"periodo_fin": "La fecha de fin debe ser posterior o igual al inicio"}},
            )

        return fecha_inicio, fecha_fin

    @staticmethod
    def _validar_grupo(grupo_utn_id):
        try:
            MemoriaService._validar_id(grupo_utn_id, "grupo_utn_id")
        except ValidationError as error:
            raise ValidationError(str(error), details={"fields": {"grupo_utn_id": "Seleccione una UCT válida"}}) from error
        grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id, with_for_update={"of": GrupoInvestigacionUtn})
        if grupo is None or grupo.deleted_at is not None:
            raise ValidationError("Debe seleccionar una UCT activa", details={"fields": {"grupo_utn_id": "Seleccione una UCT activa"}})
        return grupo.id

    @staticmethod
    def _nombre_grupo_historial(valor):
        if valor in (None, ""):
            return valor
        try:
            grupo_id = int(valor)
        except (TypeError, ValueError):
            return valor
        grupo = db.session.get(GrupoInvestigacionUtn, grupo_id)
        return grupo.nombre_sigla_grupo if grupo else valor

    @staticmethod
    def _validar_solapamiento(periodo_inicio, periodo_fin, grupo_utn_id, memoria_id_excluida=None):
        query = Memoria.query.filter(
            Memoria.deleted_at.is_(None),
            Memoria.grupo_utn_id == grupo_utn_id,
            Memoria.periodo_inicio <= periodo_fin,
            Memoria.periodo_fin >= periodo_inicio,
        )
        if memoria_id_excluida is not None:
            query = query.filter(Memoria.id != memoria_id_excluida)
        if query.first() is not None:
            raise ConflictError(
                "El período se superpone con otra memoria. Verifique las fechas e intente nuevamente.",
                details={"fields": {"periodo_inicio": "Revise el período: se superpone con otra memoria", "periodo_fin": "Revise el período: se superpone con otra memoria"}},
            )

    @staticmethod
    def _validar_unica_memoria_activa(grupo_utn_id, memoria_id_excluida: int | None = None):
        query = Memoria.query.filter(Memoria.deleted_at.is_(None), Memoria.grupo_utn_id == grupo_utn_id)

        if memoria_id_excluida is not None:
            query = query.filter(Memoria.id != memoria_id_excluida)

        memorias = query.all()
        for memoria in memorias:
            version_actual = memoria.version_actual
            if (
                version_actual
                and version_actual.deleted_at is None
                and version_actual.estado != EstadoMemoria.CERRADA
            ):
                raise ConflictError(
                    "Solo puede existir una memoria activa a la vez por UCT",
                    details={"fields": {"grupo_utn_id": "La UCT ya tiene una memoria activa"}},
                )

    @staticmethod
    def _resolver_fecha_apertura(fecha_apertura):
        # Se admite que la fecha de apertura llegue desde el usuario, pero si
        # no se informa usamos el instante actual para no bloquear el alta.
        if fecha_apertura in (None, ""):
            return datetime.utcnow()

        if isinstance(fecha_apertura, datetime):
            return fecha_apertura

        if isinstance(fecha_apertura, str):
            valor = fecha_apertura.strip()

            for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(valor, formato)
                except ValueError:
                    pass

            try:
                return datetime.combine(
                    datetime.strptime(valor, "%Y-%m-%d").date(),
                    datetime.min.time()
                )
            except ValueError:
                pass

        raise ValidationError(
            "La fecha_apertura debe tener formato YYYY-MM-DD o YYYY-MM-DD HH:MM:SS",
            details={"fields": {"fecha_apertura": "Ingrese una fecha de apertura válida"}},
        )

    @staticmethod
    def _resolver_fecha_evento(fecha_evento, campo: str):
        # Unifica el parseo de fechas datetime que marcan transiciones para que
        # cerrar y reabrir mantengan el mismo criterio de entrada.
        if fecha_evento in (None, ""):
            return datetime.utcnow()

        if isinstance(fecha_evento, datetime):
            return fecha_evento

        if isinstance(fecha_evento, str):
            valor = fecha_evento.strip()

            for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(valor, formato)
                except ValueError:
                    pass

            try:
                return datetime.combine(
                    datetime.strptime(valor, "%Y-%m-%d").date(),
                    datetime.min.time()
                )
            except ValueError:
                pass

        raise ValidationError(
            f"El campo '{campo}' debe tener formato YYYY-MM-DD o YYYY-MM-DD HH:MM:SS"
        )

    @staticmethod
    def _validar_estado(estado):
        if isinstance(estado, EstadoMemoria):
            return estado

        if isinstance(estado, str):
            valor = estado.strip().lower()
            for estado_enum in EstadoMemoria:
                if estado_enum.value == valor:
                    return estado_enum

        raise ValidationError(
            "El estado debe ser 'abierta', 'en revision' o 'cerrada'"
        )

    @staticmethod
    def _get_memoria_or_404(memoria_id: int, bloquear=False):
        memoria = db.session.get(
            Memoria,
            MemoriaService._validar_id(memoria_id, "memoria_id"),
            **({"with_for_update": {"of": Memoria}} if bloquear else {})
        )
        if not memoria or memoria.deleted_at is not None:
            raise NotFoundError("Memoria no encontrada")
        return memoria

    @staticmethod
    def _get_version_actual_or_404(memoria: Memoria):
        if not memoria.version_actual or memoria.version_actual.deleted_at is not None:
            raise NotFoundError("La memoria no tiene una version actual valida")
        return memoria.version_actual

    @staticmethod
    def _get_version_or_404(memoria_version_id: int):
        version = db.session.get(
            MemoriaVersion,
            MemoriaService._validar_id(memoria_version_id, "memoria_version_id")
        )
        if not version or version.deleted_at is not None:
            raise NotFoundError("La version de memoria no existe")
        return version

    @staticmethod
    def _validar_transicion_estado(estado_actual: EstadoMemoria, nuevo_estado: EstadoMemoria):
        transiciones_validas = {
            EstadoMemoria.ABIERTA: {
                EstadoMemoria.EN_REVISION,
                EstadoMemoria.CERRADA
            },
            EstadoMemoria.EN_REVISION: {
                EstadoMemoria.ABIERTA,
                EstadoMemoria.CERRADA
            },
            EstadoMemoria.CERRADA: set()
        }

        if nuevo_estado == estado_actual:
            raise ConflictError("La memoria ya se encuentra en ese estado")

        if nuevo_estado not in transiciones_validas[estado_actual]:
            raise ConflictError(
                f"No se puede cambiar el estado de '{estado_actual.value}' a '{nuevo_estado.value}'"
            )

    @staticmethod
    def _obtener_siguiente_numero_version(memoria: Memoria):
        if not memoria.versiones:
            return 1
        return max(version.numero_version for version in memoria.versiones) + 1

    @staticmethod
    def _crear_version_inicial(memoria: Memoria, user_id: int, fecha_apertura=None):
        # La memoria nace con una version activa para que el resto de la capa
        # de negocio siempre trabaje contra una "memoria viva" bien definida.
        version = MemoriaVersion(
            numero_version=1,
            fecha_apertura=MemoriaService._resolver_fecha_apertura(fecha_apertura),
            fecha_cierre=None,
            estado=EstadoMemoria.ABIERTA,
            memoria=memoria,
            created_by=user_id
        )
        db.session.add(version)
        db.session.flush()
        memoria.version_actual_id = version.id
        return version

    @staticmethod
    def _contar_elementos_version(version: MemoriaVersion):
        if not version or version.deleted_at is not None:
            return 0

        if version.estado != EstadoMemoria.CERRADA:
            return 0

        group_id = getattr(g, "current_grupo_utn_id", None) if has_request_context() else None
        counts = []
        for table_name in SNAPSHOT_TABLES:
            table = db.metadata.tables[table_name]
            query = select(func.count(table.c.id).label("total")).where(
                table.c.memoria_version_id == version.id,
                table.c.deleted_at.is_(None),
            )
            for column_name in ("grupo_utn_id", "grupo_id", "id_grupo_utn"):
                if group_id is not None and column_name in table.c:
                    query = query.where(table.c[column_name] == group_id)
                    break
            counts.append(query)
        totals = union_all(*counts).subquery()
        return db.session.scalar(select(func.coalesce(func.sum(totals.c.total), 0)))

    @staticmethod
    def _serializar_memoria(memoria: Memoria):
        data = memoria.serialize()
        version_actual = memoria.version_actual
        data["cantidad_elementos"] = MemoriaService._contar_elementos_version(
            version_actual
        ) if version_actual else 0
        return data

    # ==========================================
    # GET ALL
    # ==========================================

    @staticmethod
    def _consulta_memorias(activos: str = "true"):
        query = Memoria.query

        if activos == "true":
            query = query.filter(Memoria.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(Memoria.deleted_at.isnot(None))
        elif activos == "all":
            pass
        else:
            query = query.filter(Memoria.deleted_at.is_(None))

        return query.order_by(Memoria.id.desc())

    @staticmethod
    def get_all(activos: str = "true"):
        memorias = MemoriaService._consulta_memorias(activos).all()
        return [MemoriaService._serializar_memoria(memoria) for memoria in memorias]

    @staticmethod
    def get_page(page: int, per_page: int, activos: str = "true", orden: str = "asc"):
        memorias, total = paginate_query(
            MemoriaService._consulta_memorias(activos).options(
                selectinload(Memoria.versiones),
                selectinload(Memoria.version_actual),
            ), page, per_page
        )
        return [MemoriaService._serializar_memoria(memoria) for memoria in memorias], total

    # ==========================================
    # GET BY ID
    # ==========================================

    @staticmethod
    def get_by_id(memoria_id: int):
        memoria = db.session.get(
            Memoria,
            MemoriaService._validar_id(memoria_id, "memoria_id")
        )
        if not memoria:
            raise NotFoundError("Memoria no encontrada")
        data = MemoriaService._serializar_memoria(memoria)
        data["versiones"] = [
            version.serialize()
            for version in memoria.versiones
            if version.deleted_at is None
        ]
        return data

    @staticmethod
    def get_investigadores_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "investigador_memoria_version")
                or obtener_snapshots_investigadores_por_memoria_version(version.id))

    @staticmethod
    def get_becarios_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "becario_memoria_version")
                or obtener_snapshots_becarios_por_memoria_version(version.id))

    @staticmethod
    def get_personal_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "personal_memoria_version")
                or obtener_snapshots_personal_por_memoria_version(version.id))

    @staticmethod
    def get_proyectos_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "proyecto_investigacion_memoria_version")
                or ProyectoInvestigacionService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_actividades_docencia_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "actividad_docencia_memoria_version")
                or ActividadDocenciaService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_participaciones_relevantes_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "participacion_relevante_memoria_version")
                or ParticipacionRelevanteService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_documentacion_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "documentacion_bibliografica_memoria_version")
                or DocumentacionBibliograficaService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_equipamiento_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "equipamiento_memoria_version")
                or EquipamientoService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_erogaciones_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "movimiento_memoria_version")
                or MovimientoFinancieroService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_transferencias_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "transferencia_socio_productiva_memoria_version")
                or TransferenciaSocioProductivaService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_trabajos_reunion_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "trabajo_reunion_cientifica_memoria_version")
                or TrabajoReunionCientificaService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_trabajos_revista_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "trabajos_revista_memoria_version")
                or TrabajosRevistasReferatoService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_distinciones_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "distincion_recibida_memoria_version")
                or DistincionRecibidaService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_registros_propiedad_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "registros_propiedad_memoria_version")
                or RegistrosPropiedadService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_articulos_divulgacion_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "articulo_divulgacion_memoria_version")
                or ArticuloDivulgacionService.obtener_snapshots_por_memoria_version(version.id))

    @staticmethod
    def get_visitas_snapshot(memoria_id: int, memoria_version_id: int):
        memoria = MemoriaService._get_memoria_or_404(memoria_id)
        version = MemoriaService._get_version_or_404(memoria_version_id)

        if version.memoria_id != memoria.id:
            raise NotFoundError("La version no pertenece a la memoria indicada")

        return (MemoriaService._snapshot_page_or_none(version.id, "visita_academica_memoria_version")
                or obtener_snapshots_visitas_por_memoria_version(version.id))

    # ==========================================
    # CREATE
    # ==========================================

    @staticmethod
    def create(data: dict, user_id: int):
        MemoriaService._validar_payload(data)
        MemoriaService._validar_id(user_id, "user_id")
        periodo_inicio, periodo_fin = MemoriaService._validar_periodos(
            data.get("periodo_inicio"),
            data.get("periodo_fin")
        )
        grupo_utn_id = MemoriaService._validar_grupo(data.get("grupo_utn_id"))
        MemoriaService._validar_solapamiento(periodo_inicio, periodo_fin, grupo_utn_id)
        MemoriaService._validar_unica_memoria_activa(grupo_utn_id)

        memoria = Memoria(
            grupo_utn_id=grupo_utn_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            created_by=user_id
        )

        try:
            db.session.add(memoria)
            db.session.flush()

            MemoriaService._crear_version_inicial(
                memoria,
                user_id,
                data.get("fecha_apertura")
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return memoria.serialize()

    # ==========================================
    # UPDATE
    # ==========================================

    @staticmethod
    def update(memoria_id: int, data: dict, user_id: int):
        MemoriaService._validar_payload(data)
        MemoriaService._validar_id(user_id, "user_id")
        memoria = MemoriaService._get_memoria_or_404(memoria_id, bloquear=True)
        if set(data) - {"periodo_inicio", "periodo_fin", "grupo_utn_id"}:
            raise ValidationError("Solo se permite corregir las fechas del período")
        if any(v.estado == EstadoMemoria.CERRADA or v.fecha_cierre is not None
               for v in memoria.versiones):
            raise ConflictError("El período no puede modificarse porque existe una versión cerrada")
        grupo_id = memoria.grupo_utn_id
        if "grupo_utn_id" in data:
            if grupo_id is not None and data["grupo_utn_id"] != grupo_id:
                raise ConflictError("La UCT de la memoria no puede cambiarse")
            grupo_id = MemoriaService._validar_grupo(data["grupo_utn_id"])
        elif grupo_id is not None:
            MemoriaService._validar_grupo(grupo_id)
        if grupo_id is None:
            raise ValidationError("Debe asociar la memoria a una UCT", details={"fields": {"grupo_utn_id": "Seleccione una UCT"}})
        inicio, fin = MemoriaService._validar_periodos(
            data.get("periodo_inicio", memoria.periodo_inicio.isoformat()),
            data.get("periodo_fin", memoria.periodo_fin.isoformat()),
        )
        cambios = [(campo, getattr(memoria, campo), valor)
                   for campo, valor in (("periodo_inicio", inicio), ("periodo_fin", fin))
                   if getattr(memoria, campo) != valor]
        if grupo_id != memoria.grupo_utn_id:
            cambios.append(("grupo_utn_id", memoria.grupo_utn_id, grupo_id))
            MemoriaService._validar_unica_memoria_activa(grupo_id, memoria.id)
        if not cambios:
            return memoria.serialize()
        from modules.informes.models.informe import Informe
        if has_app_context() and Informe.query.filter_by(memoria_id=memoria.id).filter(Informe.deleted_at.is_(None)).first():
            raise ConflictError("El período de la Memoria no puede modificarse mientras tiene informes activos.")
        MemoriaService._validar_solapamiento(inicio, fin, grupo_id, memoria.id)
        try:
            for campo, anterior, nuevo in cambios:
                anterior_auditado = anterior
                nuevo_auditado = nuevo
                if campo == "grupo_utn_id":
                    anterior_auditado = MemoriaService._nombre_grupo_historial(anterior)
                    nuevo_auditado = MemoriaService._nombre_grupo_historial(nuevo)
                AuditoriaService.registrar_cambios(
                    entidad="memoria", registro_id=memoria.id,
                    cambios={
                        campo: AuditoriaService.construir_cambio(
                            anterior_auditado,
                            nuevo_auditado,
                        )
                    },
                    user_id=user_id, memoria_id=memoria.id,
                )
                setattr(memoria, campo, nuevo)
            memoria.mark_updated(user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return memoria.serialize()

    @staticmethod
    def get_historial(memoria_id: int):
        MemoriaService._get_memoria_or_404(memoria_id)
        historial = AuditoriaService.obtener_historial_entidad("memoria", memoria_id)
        eventos = historial["data"] if isinstance(historial, dict) else historial
        for item in eventos:
            if item.get("campo") != "grupo_utn_id":
                continue
            item["valor_anterior"] = MemoriaService._nombre_grupo_historial(
                item.get("valor_anterior")
            )
            item["valor_nuevo"] = MemoriaService._nombre_grupo_historial(
                item.get("valor_nuevo")
            )
        return historial

    # ==========================================
    # SOFT DELETE
    # ==========================================

    @staticmethod
    def delete(memoria_id: int, user_id: int):
        MemoriaService._validar_id(user_id, "user_id")
        memoria = MemoriaService._get_memoria_or_404(memoria_id, bloquear=True)
        from modules.informes.models.informe import Informe
        if has_app_context() and Informe.query.filter_by(memoria_id=memoria.id).filter(Informe.deleted_at.is_(None)).first():
            raise ConflictError("La Memoria tiene informes activos y no puede eliminarse.")

        # El borrado sigue la estrategia general del sistema: se marca como
        # inactiva para preservar trazabilidad y no perder referencias.
        memoria.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Memoria eliminada correctamente"}

    # ==========================================
    # CAMBIAR ESTADO
    # ==========================================

    @staticmethod
    def change_status(memoria_id: int, data: dict, user_id: int | None = None):
        MemoriaService._validar_payload(data)
        memoria = MemoriaService._get_memoria_or_404(memoria_id, bloquear=True)
        if memoria.grupo_utn_id is None:
            raise ConflictError("Debe asociar la memoria a una UCT antes de continuar")
        MemoriaService._validar_grupo(memoria.grupo_utn_id)
        version_actual = MemoriaService._get_version_actual_or_404(memoria)
        nuevo_estado = MemoriaService._validar_estado(data.get("estado"))

        MemoriaService._validar_transicion_estado(
            version_actual.estado,
            nuevo_estado
        )
        estado_anterior = version_actual.estado

        try:
            # Mientras la version siga viva, solo muta su estado. La unica salida
            # definitiva de la version actual es el estado cerrada.
            version_actual.estado = nuevo_estado

            if nuevo_estado == EstadoMemoria.CERRADA:
                # Collect snapshots before query-triggered flushes; commit still validates
                # every pending write under the request UCT policy.
                with (db.session.no_autoflush if has_app_context() else nullcontext()):
                    version_actual.contexto_institucional = snapshot_contexto_institucional(version_actual)
                    version_actual.fecha_cierre = MemoriaService._resolver_fecha_evento(
                        data.get("fecha_cierre"),
                        "fecha_cierre"
                    )
                    if user_id is not None:
                        version_actual.mark_updated(user_id)
                        snapshot_investigadores_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        snapshot_becarios_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        snapshot_personal_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        ProyectoInvestigacionService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        ActividadDocenciaService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        ParticipacionRelevanteService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        DocumentacionBibliograficaService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        EquipamientoService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        MovimientoFinancieroService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        TransferenciaSocioProductivaService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        TrabajoReunionCientificaService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        TrabajosRevistasReferatoService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        DistincionRecibidaService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        RegistrosPropiedadService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        ArticuloDivulgacionService.snapshot_para_memoria_version(
                            version_actual,
                            user_id
                        )
                        snapshot_visitas_para_memoria_version(
                            version_actual,
                            user_id
                        )
            else:
                version_actual.fecha_cierre = None
                if user_id is not None:
                    version_actual.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="memoria",
                registro_id=memoria.id,
                cambios={
                    "estado": AuditoriaService.construir_cambio(
                        estado_anterior,
                        nuevo_estado,
                    )
                },
                user_id=user_id,
                memoria_id=memoria.id,
                memoria_version_id=version_actual.id,
            )
            if user_id is not None:
                memoria.mark_updated(user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return memoria.serialize()

    # ==========================================
    # REABRIR (NUEVA VERSION)
    # ==========================================

    @staticmethod
    def reopen(memoria_id: int, user_id: int, data: dict | None = None):
        MemoriaService._validar_id(user_id, "user_id")
        memoria = MemoriaService._get_memoria_or_404(memoria_id, bloquear=True)
        if memoria.grupo_utn_id is None:
            raise ConflictError("Debe asociar la memoria a una UCT antes de continuar")
        MemoriaService._validar_grupo(memoria.grupo_utn_id)
        version_actual = MemoriaService._get_version_actual_or_404(memoria)
        data = data or {}

        if version_actual.estado != EstadoMemoria.CERRADA:
            raise ConflictError(
                "Solo se puede crear una nueva version a partir de una memoria cerrada"
            )

        MemoriaService._validar_unica_memoria_activa(memoria.grupo_utn_id, memoria_id_excluida=memoria.id)

        # Reabrir no muta la version historica cerrada: crea una nueva version
        # editable y la convierte en la version actual de la memoria.
        nueva_version = MemoriaVersion(
            numero_version=MemoriaService._obtener_siguiente_numero_version(memoria),
            fecha_apertura=MemoriaService._resolver_fecha_apertura(
                data.get("fecha_apertura")
            ),
            fecha_cierre=None,
            estado=EstadoMemoria.ABIERTA,
            memoria=memoria,
            created_by=user_id
        )

        try:
            db.session.add(nueva_version)
            db.session.flush()
            memoria.version_actual_id = nueva_version.id
            memoria.mark_updated(user_id)
            AuditoriaService.registrar_evento_relacion(
                entidad="memoria",
                registro_id=memoria.id,
                relacion="versiones",
                accion="reapertura",
                detalle={
                    "version_anterior": version_actual.numero_version,
                    "version_nueva": nueva_version.numero_version,
                },
                user_id=user_id,
                memoria_id=memoria.id,
                memoria_version_id=nueva_version.id,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return memoria.serialize()
