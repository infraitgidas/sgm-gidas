from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload, lazyload, selectinload

from modules.recursos.models.becas import Beca, Beca_Becario
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.recursos.services.saldo_financiero_service import SaldoFinancieroService
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.personal.models.personal import Becario, Investigador, Personal
from modules.proyectos.models.proyecto_investigacion import (
    BecarioProyecto,
    InvestigadorProyecto,
    ProyectoInvestigacion,
)
from modules.transferencia.models.transferencia_socio import TransferenciaSocioProductiva


class DashboardService:
    @staticmethod
    def get_resumen(
        anios: int = 5,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        solo_becarios_con_beca_activa: bool = False
    ):
        hoy = date.today()
        todos_los_proyectos = ProyectoInvestigacion.query.options(
            lazyload("*"),
            joinedload(ProyectoInvestigacion.tipo_proyecto),
            joinedload(ProyectoInvestigacion.fuente_financiamiento),
            selectinload(ProyectoInvestigacion.distinciones),
        ).all()
        investigadores = Investigador.query.options(lazyload("*")).all()
        becarios = Becario.query.options(
            selectinload(Becario.tipo_formacion),
        ).all()
        personal = Personal.query.options(lazyload("*")).all()
        grupos = GrupoInvestigacionUtn.query.options(lazyload("*")).all()
        fuentes = FuenteFinanciamiento.query.all()
        todas_las_becas = Beca.query.all()
        asignaciones_beca = Beca_Becario.query.all()
        participaciones_investigador = InvestigadorProyecto.query.all()
        participaciones_becario = BecarioProyecto.query.all()
        todas_las_erogaciones = MovimientoFinanciero.query.options(
            joinedload(MovimientoFinanciero.categoria_erogacion)
        ).filter(MovimientoFinanciero.deleted_at.is_(None)).all()
        todas_las_transferencias = TransferenciaSocioProductiva.query.options(
            joinedload(TransferenciaSocioProductiva.tipo_contrato_transferencia),
        ).all()

        proyectos = DashboardService._filtrar_intervalo(
            todos_los_proyectos,
            fecha_desde,
            fecha_hasta,
            lambda proyecto: proyecto.fecha_inicio,
            lambda proyecto: proyecto.fecha_fin
        )
        erogaciones = DashboardService._filtrar_fecha_simple(
            todas_las_erogaciones,
            fecha_desde,
            fecha_hasta,
            lambda erogacion: erogacion.fecha
        )
        saldo_financiero = SaldoFinancieroService.calcular(
            None, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        transferencias = DashboardService._filtrar_intervalo(
            todas_las_transferencias,
            fecha_desde,
            fecha_hasta,
            lambda transferencia: transferencia.fecha_inicio,
            lambda transferencia: transferencia.fecha_fin
        )
        becas = DashboardService._filtrar_becas_por_asignacion(
            todas_las_becas,
            asignaciones_beca,
            fecha_desde,
            fecha_hasta
        )
        becarios_para_distribucion = (
            DashboardService._filtrar_becarios_con_beca_activa(
                becarios,
                asignaciones_beca,
                fecha_desde,
                fecha_hasta
            )
            if solo_becarios_con_beca_activa
            else becarios
        )

        proyectos_activos = [
            proyecto for proyecto in proyectos
            if proyecto.fecha_fin is None or proyecto.fecha_fin >= hoy
        ]
        proyecto_ids_activos = {proyecto.id for proyecto in proyectos_activos}
        investigadores_con_proyectos_activos = (
            DashboardService._contar_investigadores_con_proyectos_activos(
                participaciones_investigador,
                proyecto_ids_activos,
                fecha_desde,
                fecha_hasta,
                hoy
            )
        )
        becarios_con_proyectos_activos = (
            DashboardService._contar_becarios_con_proyectos_activos(
                participaciones_becario,
                proyecto_ids_activos,
                fecha_desde,
                fecha_hasta,
                hoy
            )
        )

        monto_total_proyectos = sum(
            float(proyecto.monto_destinado or 0)
            for proyecto in proyectos
        )

        proyectos_con_monto = [
            float(proyecto.monto_destinado)
            for proyecto in proyectos
            if proyecto.monto_destinado is not None
        ]

        resumen = {
            "total_proyectos": len(proyectos),
            "proyectos_activos": len(proyectos_activos),
            "proyectos_finalizados": len(proyectos) - len(proyectos_activos),
            "total_investigadores": len(investigadores),
            "investigadores_con_proyectos_activos": (
                investigadores_con_proyectos_activos
            ),
            "total_becarios": len(becarios_para_distribucion),
            "becarios_con_proyectos_activos": becarios_con_proyectos_activos,
            "total_personal": len(personal),
            "total_grupos": len(grupos),
            "total_becas": len(becas),
            "total_erogaciones": len(erogaciones),
            "total_ingresos": str(saldo_financiero.total_ingresos),
            "total_egresos": str(saldo_financiero.total_egresos),
            "saldo_financiero": str(saldo_financiero.saldo_disponible),
            "egresos_corrientes": str(sum(
                (item.monto_equivalente_ars or item.monto for item in erogaciones
                 if item.tipo_movimiento == "EGRESO"
                 and item.categoria_erogacion
                 and item.categoria_erogacion.codigo == "CORRIENTE"),
                start=Decimal("0"),
            )),
            "egresos_capital": str(sum(
                (item.monto_equivalente_ars or item.monto for item in erogaciones
                 if item.tipo_movimiento == "EGRESO"
                 and item.categoria_erogacion
                 and item.categoria_erogacion.codigo == "CAPITAL"),
                start=Decimal("0"),
            )),
            "total_transferencias": len(transferencias),
            "total_fuentes_financiamiento": len(fuentes),
            "monto_total_proyectos": round(monto_total_proyectos, 2),
            "promedio_monto_proyecto": round(
                monto_total_proyectos / len(proyectos_con_monto),
                2
            ) if proyectos_con_monto else 0,
        }

        distribuciones = {
            "proyectos_por_tipo": DashboardService._proyectos_por_tipo(proyectos),
            "proyectos_por_fuente": DashboardService._proyectos_por_fuente(proyectos),
            "proyectos_por_distinciones": (
                DashboardService._proyectos_por_distinciones(proyectos)
            ),
            "erogaciones_por_tipo": DashboardService._erogaciones_por_tipo(
                erogaciones
            ),
            "transferencias_por_tipo_contrato": (
                DashboardService._transferencias_por_tipo_contrato(
                    transferencias
                )
            ),
            "becarios_por_tipo_formacion": (
                DashboardService._becarios_por_tipo_formacion(
                    becarios_para_distribucion
                )
            ),
            "integrantes_por_grupo": DashboardService._integrantes_por_grupo(
                grupos,
                hoy,
                {proyecto.id for proyecto in proyectos},
                investigadores, becarios, personal, todos_los_proyectos,
            ),
        }

        series = {
            "proyectos_por_anio_inicio": DashboardService._proyectos_por_anio_inicio(
                proyectos,
                anios
            ),
            "proyectos_finalizados_por_anio": (
                DashboardService._proyectos_finalizados_por_anio(proyectos, anios)
            ),
            "monto_proyectos_por_anio_inicio": (
                DashboardService._monto_proyectos_por_anio_inicio(proyectos, anios)
            ),
        }

        alertas = {
            "proyectos_sin_financiamiento": len([
                proyecto for proyecto in proyectos
                if proyecto.fuente_financiamiento is None
            ]),
            "proyectos_sin_grupo": len([
                proyecto for proyecto in proyectos
                if proyecto.grupo_utn is None
            ]),
            "proyectos_por_vencer": DashboardService._proyectos_por_vencer(
                proyectos_activos,
                hoy
            ),
        }

        return {
            "generado_en": datetime.utcnow().isoformat() + "Z",
            "parametros": {
                "anios": anios,
                "fecha_desde": (
                    fecha_desde.isoformat() if fecha_desde else None
                ),
                "fecha_hasta": (
                    fecha_hasta.isoformat() if fecha_hasta else None
                ),
                "solo_becarios_con_beca_activa": solo_becarios_con_beca_activa,
            },
            "resumen": resumen,
            "distribuciones": distribuciones,
            "series": series,
            "alertas": alertas,
        }

    @staticmethod
    def _proyectos_por_tipo(proyectos):
        contador = Counter(
            proyecto.tipo_proyecto.nombre
            if proyecto.tipo_proyecto else "Sin tipo"
            for proyecto in proyectos
        )

        return [
            {
                "tipo": tipo,
                "total": total
            }
            for tipo, total in contador.most_common()
        ]

    @staticmethod
    def _proyectos_por_fuente(proyectos):
        contador = Counter(
            proyecto.fuente_financiamiento.nombre
            if proyecto.fuente_financiamiento else "Sin fuente"
            for proyecto in proyectos
        )

        return [
            {
                "fuente": fuente,
                "total": total
            }
            for fuente, total in contador.most_common()
        ]

    @staticmethod
    def _proyectos_por_distinciones(proyectos):
        con_distinciones = sum(
            1 for proyecto in proyectos
            if len(proyecto.distinciones) > 0
        )
        sin_distinciones = len(proyectos) - con_distinciones

        return [
            {
                "categoria": "Con distinciones",
                "total": con_distinciones
            },
            {
                "categoria": "Sin distinciones",
                "total": sin_distinciones
            }
        ]

    @staticmethod
    def _integrantes_por_grupo(grupos, hoy, proyecto_ids_filtrados=None,
                              investigadores=None, becarios=None, personal=None,
                              proyectos=None):
        data = []
        # Reuse the scoped rows already collected for the dashboard instead of
        # issuing another query for each group and each collection.
        counts = [Counter(item.grupo_utn_id for item in rows) if rows is not None else None
                  for rows in (investigadores, becarios, personal)]

        for grupo in grupos:
            proyectos_activos = sum(
                1 for proyecto in (proyectos if proyectos is not None else grupo.proyectos_investigacion)
                if (
                    (proyectos is None or proyecto.grupo_utn_id == grupo.id)
                    and
                    (proyecto_ids_filtrados is None or proyecto.id in proyecto_ids_filtrados)
                    and (proyecto.fecha_fin is None or proyecto.fecha_fin >= hoy)
                )
            )

            data.append({
                "grupo_id": grupo.id,
                "grupo": grupo.nombre_sigla_grupo,
                "unidad_academica": grupo.nombre_unidad_academica,
                "investigadores": counts[0][grupo.id] if counts[0] is not None else len(grupo.investigadores),
                "becarios": counts[1][grupo.id] if counts[1] is not None else len(grupo.becarios),
                "personal": counts[2][grupo.id] if counts[2] is not None else len(grupo.personal),
                "total_integrantes": (
                    sum(counter[grupo.id] for counter in counts)
                    if all(counter is not None for counter in counts)
                    else len(grupo.investigadores) + len(grupo.becarios) + len(grupo.personal)
                ),
                "proyectos_activos": proyectos_activos,
            })

        data.sort(key=lambda item: item["total_integrantes"], reverse=True)
        return data

    @staticmethod
    def _filtrar_fecha_simple(items, fecha_desde, fecha_hasta, get_fecha):
        if fecha_desde is None and fecha_hasta is None:
            return items

        filtrados = []
        for item in items:
            fecha = get_fecha(item)
            if fecha is None:
                continue
            if fecha_desde and fecha < fecha_desde:
                continue
            if fecha_hasta and fecha > fecha_hasta:
                continue
            filtrados.append(item)

        return filtrados

    @staticmethod
    def _filtrar_intervalo(items, fecha_desde, fecha_hasta, get_inicio, get_fin):
        if fecha_desde is None and fecha_hasta is None:
            return items

        filtrados = []
        for item in items:
            if DashboardService._intervalo_solapa(
                get_inicio(item),
                get_fin(item),
                fecha_desde,
                fecha_hasta
            ):
                filtrados.append(item)

        return filtrados

    @staticmethod
    def _intervalo_solapa(inicio, fin, fecha_desde, fecha_hasta):
        inicio = inicio or date.min
        fin = fin or date.max
        fecha_desde = fecha_desde or date.min
        fecha_hasta = fecha_hasta or date.max
        return inicio <= fecha_hasta and fin >= fecha_desde

    @staticmethod
    def _filtrar_becas_por_asignacion(
        becas,
        asignaciones_beca,
        fecha_desde,
        fecha_hasta
    ):
        if fecha_desde is None and fecha_hasta is None:
            return becas

        beca_ids_en_rango = {
            asignacion.id_beca
            for asignacion in asignaciones_beca
            if DashboardService._intervalo_solapa(
                asignacion.fecha_inicio,
                asignacion.fecha_fin,
                fecha_desde,
                fecha_hasta
            )
        }

        return [
            beca for beca in becas
            if beca.id in beca_ids_en_rango
        ]

    @staticmethod
    def _filtrar_becarios_con_beca_activa(
        becarios,
        asignaciones_beca,
        fecha_desde,
        fecha_hasta
    ):
        becario_ids_en_rango = {
            asignacion.id_becario
            for asignacion in asignaciones_beca
            if DashboardService._intervalo_solapa(
                asignacion.fecha_inicio,
                asignacion.fecha_fin,
                fecha_desde,
                fecha_hasta
            )
        }

        return [
            becario for becario in becarios
            if becario.id in becario_ids_en_rango
        ]

    @staticmethod
    def _contar_investigadores_con_proyectos_activos(
        participaciones,
        proyecto_ids_activos,
        fecha_desde,
        fecha_hasta,
        hoy
    ):
        investigador_ids = {
            participacion.id_investigador
            for participacion in participaciones
            if (
                participacion.id_proyecto in proyecto_ids_activos
                and DashboardService._intervalo_solapa(
                    participacion.fecha_inicio,
                    participacion.fecha_fin,
                    fecha_desde,
                    fecha_hasta or hoy
                )
            )
        }
        return len(investigador_ids)

    @staticmethod
    def _contar_becarios_con_proyectos_activos(
        participaciones,
        proyecto_ids_activos,
        fecha_desde,
        fecha_hasta,
        hoy
    ):
        becario_ids = {
            participacion.id_becario
            for participacion in participaciones
            if (
                participacion.id_proyecto in proyecto_ids_activos
                and DashboardService._intervalo_solapa(
                    participacion.fecha_inicio,
                    participacion.fecha_fin,
                    fecha_desde,
                    fecha_hasta or hoy
                )
            )
        }
        return len(becario_ids)

    @staticmethod
    def _erogaciones_por_tipo(erogaciones):
        agrupado = defaultdict(lambda: {
            "tipo": "Sin tipo",
            "total_registros": 0,
            "total_egresos": Decimal("0"),
            "total_ingresos": Decimal("0"),
            "balance": Decimal("0"),
        })

        for erogacion in erogaciones:
            tipo = (
                "Ingresos" if erogacion.tipo_movimiento == "INGRESO" else
                erogacion.categoria_erogacion.nombre
                if erogacion.categoria_erogacion else "Sin categoría"
            )

            agrupado[tipo]["tipo"] = tipo
            agrupado[tipo]["total_registros"] += 1
            if erogacion.tipo_movimiento == "EGRESO":
                agrupado[tipo]["total_egresos"] += Decimal(str(erogacion.monto_equivalente_ars or erogacion.monto))
            else:
                agrupado[tipo]["total_ingresos"] += Decimal(str(erogacion.monto_equivalente_ars or erogacion.monto))
            agrupado[tipo]["balance"] = (
                agrupado[tipo]["total_ingresos"]
                - agrupado[tipo]["total_egresos"]
            )

        data = list(agrupado.values())
        for item in data:
            item["total_egresos"] = float(item["total_egresos"])
            item["total_ingresos"] = float(item["total_ingresos"])
            item["balance"] = float(item["balance"])

        data.sort(key=lambda item: item["total_egresos"], reverse=True)
        return data

    @staticmethod
    def _transferencias_por_tipo_contrato(transferencias):
        agrupado = defaultdict(lambda: {
            "tipo_contrato": "Sin tipo",
            "total": 0,
            "monto_total": 0.0,
        })

        for transferencia in transferencias:
            tipo = (
                transferencia.tipo_contrato_transferencia.nombre
                if transferencia.tipo_contrato_transferencia else "Sin tipo"
            )

            agrupado[tipo]["tipo_contrato"] = tipo
            agrupado[tipo]["total"] += 1
            agrupado[tipo]["monto_total"] += float(transferencia.monto or 0)

        data = list(agrupado.values())
        for item in data:
            item["monto_total"] = round(item["monto_total"], 2)

        data.sort(key=lambda item: item["total"], reverse=True)
        return data

    @staticmethod
    def _becarios_por_tipo_formacion(becarios):
        contador = Counter(
            becario.tipo_formacion.nombre
            if becario.tipo_formacion else "Sin tipo"
            for becario in becarios
        )

        return [
            {
                "tipo_formacion": tipo_formacion,
                "total": total
            }
            for tipo_formacion, total in contador.most_common()
        ]

    @staticmethod
    def _proyectos_por_anio_inicio(proyectos, anios):
        limite = date.today().year - max(anios - 1, 0)
        contador = Counter(
            proyecto.fecha_inicio.year
            for proyecto in proyectos
            if proyecto.fecha_inicio and proyecto.fecha_inicio.year >= limite
        )

        return DashboardService._build_year_series(contador, limite)

    @staticmethod
    def _proyectos_finalizados_por_anio(proyectos, anios):
        limite = date.today().year - max(anios - 1, 0)
        contador = Counter(
            proyecto.fecha_fin.year
            for proyecto in proyectos
            if proyecto.fecha_fin and proyecto.fecha_fin.year >= limite
        )

        return DashboardService._build_year_series(contador, limite)

    @staticmethod
    def _monto_proyectos_por_anio_inicio(proyectos, anios):
        limite = date.today().year - max(anios - 1, 0)
        acumulado = defaultdict(float)

        for proyecto in proyectos:
            if (
                proyecto.fecha_inicio
                and proyecto.fecha_inicio.year >= limite
                and proyecto.monto_destinado is not None
            ):
                acumulado[proyecto.fecha_inicio.year] += float(
                    proyecto.monto_destinado
                )

        return [
            {
                "anio": anio,
                "total": round(acumulado.get(anio, 0), 2)
            }
            for anio in range(limite, date.today().year + 1)
        ]

    @staticmethod
    def _build_year_series(contador, limite):
        return [
            {
                "anio": anio,
                "total": contador.get(anio, 0)
            }
            for anio in range(limite, date.today().year + 1)
        ]

    @staticmethod
    def _proyectos_por_vencer(proyectos_activos, hoy):
        proximos = []

        for proyecto in proyectos_activos:
            if proyecto.fecha_fin is None:
                continue

            dias_restantes = (proyecto.fecha_fin - hoy).days
            if 0 <= dias_restantes <= 90:
                proximos.append({
                    "id": proyecto.id,
                    "codigo_proyecto": proyecto.codigo_proyecto,
                    "nombre_proyecto": proyecto.nombre_proyecto,
                    "fecha_fin": proyecto.fecha_fin.isoformat(),
                    "dias_restantes": dias_restantes,
                    "grupo": (
                        proyecto.grupo_utn.nombre_sigla_grupo
                        if proyecto.grupo_utn else None
                    ),
                })

        proximos.sort(key=lambda item: item["dias_restantes"])
        return proximos
