"""Saldo derivado de movimientos activos de una UCT."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from flask import g, has_request_context
from sqlalchemy import case, func, select

from extension import db
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.shared.exceptions import ConflictError, NotFoundError


@dataclass(frozen=True)
class ResumenFinanciero:
    total_ingresos: Decimal
    total_egresos: Decimal
    cantidad_movimientos: int

    @property
    def saldo_disponible(self) -> Decimal:
        return self.total_ingresos - self.total_egresos

    def serialize(self) -> dict:
        return {
            "moneda": "ARS",
            "total_ingresos": str(self.total_ingresos),
            "total_egresos": str(self.total_egresos),
            "saldo_disponible": str(self.saldo_disponible),
            "cantidad_movimientos": self.cantidad_movimientos,
        }


class SaldoFinancieroService:
    @staticmethod
    def _importe_ars():
        return func.coalesce(MovimientoFinanciero.monto_equivalente_ars, MovimientoFinanciero.monto)

    @staticmethod
    def _grupo_permitido(grupo_utn_id: int | None) -> int | None:
        actual = getattr(g, "current_grupo_utn_id", None) if has_request_context() else None
        if actual is not None:
            if grupo_utn_id is not None and grupo_utn_id != actual:
                raise NotFoundError("El grupo no está disponible. Recargue la página e intente nuevamente.")
            return actual
        return grupo_utn_id

    @staticmethod
    def saldos_por_fuente(grupo_utn_id: int) -> list[dict]:
        grupo_utn_id = SaldoFinancieroService._grupo_permitido(grupo_utn_id)
        # Reutiliza la validación de grupo y moneda del saldo consolidado.
        SaldoFinancieroService.calcular(grupo_utn_id)
        ingresos = func.coalesce(func.sum(case(
            (MovimientoFinanciero.tipo_movimiento == "INGRESO", SaldoFinancieroService._importe_ars()),
            else_=0,
        )), 0)
        egresos = func.coalesce(func.sum(case(
            (MovimientoFinanciero.tipo_movimiento == "EGRESO", SaldoFinancieroService._importe_ars()),
            else_=0,
        )), 0)
        filas = db.session.execute(
            select(
                FuenteFinanciamiento.id,
                FuenteFinanciamiento.nombre,
                ingresos.label("total_ingresos"),
                egresos.label("total_egresos"),
                func.count(MovimientoFinanciero.id).label("cantidad_movimientos"),
            )
            .join(MovimientoFinanciero, MovimientoFinanciero.fuente_financiamiento_id == FuenteFinanciamiento.id)
            .where(
                MovimientoFinanciero.grupo_utn_id == grupo_utn_id,
                MovimientoFinanciero.deleted_at.is_(None),
            )
            .group_by(FuenteFinanciamiento.id, FuenteFinanciamiento.nombre)
            .order_by((ingresos - egresos).desc(), FuenteFinanciamiento.nombre.asc())
        ).all()
        return [
            {
                "fuente_id": fuente_id,
                "fuente_nombre": nombre,
                "total_ingresos": str(Decimal(str(total_ingresos))),
                "total_egresos": str(Decimal(str(total_egresos))),
                "saldo_disponible": str(Decimal(str(total_ingresos)) - Decimal(str(total_egresos))),
                "cantidad_movimientos": int(cantidad),
            }
            for fuente_id, nombre, total_ingresos, total_egresos, cantidad in filas
        ]

    @staticmethod
    def saldo_de_fuente(grupo_utn_id: int, fuente_id: int) -> Decimal:
        grupo_utn_id = SaldoFinancieroService._grupo_permitido(grupo_utn_id)
        total = db.session.scalar(select(func.coalesce(func.sum(case(
            (MovimientoFinanciero.tipo_movimiento == "INGRESO", SaldoFinancieroService._importe_ars()),
            else_=-SaldoFinancieroService._importe_ars(),
        )), 0)).where(
            MovimientoFinanciero.grupo_utn_id == grupo_utn_id,
            MovimientoFinanciero.fuente_financiamiento_id == fuente_id,
            MovimientoFinanciero.deleted_at.is_(None),
        ))
        return Decimal(str(total))

    @staticmethod
    def calcular(
        grupo_utn_id: int | None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> ResumenFinanciero:
        grupo_utn_id = SaldoFinancieroService._grupo_permitido(grupo_utn_id)
        activos = [MovimientoFinanciero.deleted_at.is_(None)]
        if grupo_utn_id is not None:
            grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id)
            if grupo is None or grupo.deleted_at is not None:
                raise NotFoundError("El grupo no está disponible. Recargue la página e intente nuevamente.")
            activos.append(MovimientoFinanciero.grupo_utn_id == grupo_utn_id)
        if fecha_desde is not None:
            activos.append(MovimientoFinanciero.fecha >= fecha_desde)
        if fecha_hasta is not None:
            activos.append(MovimientoFinanciero.fecha <= fecha_hasta)
        monedas_no_convertidas = db.session.scalar(
            select(func.count(MovimientoFinanciero.id)).where(
                *activos, MovimientoFinanciero.moneda == "USD",
                MovimientoFinanciero.monto_equivalente_ars.is_(None),
            )
        ) or 0
        if monedas_no_convertidas:
            raise ConflictError(
                "No se puede calcular un saldo consolidado sin convertir los movimientos en otras monedas."
            )

        ingresos, egresos, cantidad = db.session.execute(
            select(
                func.coalesce(func.sum(case(
                    (MovimientoFinanciero.tipo_movimiento == "INGRESO", SaldoFinancieroService._importe_ars()),
                    else_=0,
                )), 0),
                func.coalesce(func.sum(case(
                    (MovimientoFinanciero.tipo_movimiento == "EGRESO", SaldoFinancieroService._importe_ars()),
                    else_=0,
                )), 0),
                func.count(MovimientoFinanciero.id),
            ).where(*activos)
        ).one()
        return ResumenFinanciero(
            total_ingresos=Decimal(str(ingresos)),
            total_egresos=Decimal(str(egresos)),
            cantidad_movimientos=int(cantidad),
        )
