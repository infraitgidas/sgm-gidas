"""Persistencia y selección de observaciones oficiales USD/ARS."""

import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from extension import db
from modules.recursos.clients.bcra_client import BcraClient
from modules.recursos.models.tipo_cambio import TipoCambio
from modules.shared.exceptions import ConflictError

logger = logging.getLogger(__name__)


class TipoCambioService:
    @staticmethod
    def serie():
        return int(os.getenv("BCRA_RETAIL_EXCHANGE_RATE_SERIES", "7927"))

    @staticmethod
    def sincronizar(cliente=None, hoy=None):
        cliente = cliente or BcraClient()
        hoy = hoy or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
        lookback = int(os.getenv("BCRA_SYNC_LOOKBACK_DAYS", "7"))
        if lookback < 1 or lookback > 2999:
            raise ValueError("BCRA_SYNC_LOOKBACK_DAYS fuera de rango.")
        desde = hoy - timedelta(days=lookback)
        logger.info("event=bcra_exchange_rate_sync_started desde=%s hasta=%s", desde, hoy)
        try:
            cliente.verificar_variable()
            observations = cliente.consultar_tipo_cambio(desde, hoy)
            if cliente.serie != TipoCambioService.serie():
                raise ValueError("La serie BCRA del cliente no coincide con la configuración.")
            dates = {item.fecha for item in observations}
            existing = set(db.session.scalars(select(TipoCambio.fecha_cotizacion).where(
                TipoCambio.moneda_origen == "USD", TipoCambio.moneda_destino == "ARS",
                TipoCambio.serie_bcra == cliente.serie, TipoCambio.fecha_cotizacion.in_(dates),
            )).all()) if dates else set()
            inserted = 0
            for item in observations:
                if item.fecha in existing:
                    continue
                db.session.add(TipoCambio(moneda_origen="USD", moneda_destino="ARS",
                                          fecha_cotizacion=item.fecha, valor=item.valor,
                                          serie_bcra=cliente.serie, fuente="BCRA"))
                existing.add(item.fecha)
                inserted += 1
            db.session.commit()
            logger.info("event=bcra_exchange_rate_sync_completed received=%s inserted=%s existing=%s",
                        len(observations), inserted, len(observations) - inserted)
            return {"received": len(observations), "inserted": inserted,
                    "existing": len(observations) - inserted}
        except Exception:
            db.session.rollback()
            logger.exception("event=bcra_exchange_rate_sync_failed")
            raise

    @staticmethod
    def obtener_por_fecha(fecha: date):
        return db.session.scalar(select(TipoCambio).where(
            TipoCambio.moneda_origen == "USD", TipoCambio.moneda_destino == "ARS",
            TipoCambio.serie_bcra == TipoCambioService.serie(), TipoCambio.fecha_cotizacion == fecha,
        ))

    @staticmethod
    def obtener_vigente_para_fecha(fecha: date):
        cotizacion = db.session.scalar(select(TipoCambio).where(
            TipoCambio.moneda_origen == "USD", TipoCambio.moneda_destino == "ARS",
            TipoCambio.serie_bcra == TipoCambioService.serie(), TipoCambio.fecha_cotizacion <= fecha,
        ).order_by(TipoCambio.fecha_cotizacion.desc()).limit(1))
        if cotizacion is None:
            raise ConflictError("No existe una cotización oficial disponible para la fecha indicada.")
        return cotizacion
