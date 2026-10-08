"""Adaptador HTTP para la serie monetaria USD/ARS del BCRA v4."""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class BcraClientError(Exception):
    pass


@dataclass(frozen=True)
class CotizacionBCRA:
    fecha: date
    valor: Decimal
    id_variable: int


class BcraClient:
    def __init__(self, *, variable_id=None, serie=None, base_url=None, opener=None, sleep=None):
        self.variable_id = int(variable_id or os.getenv("BCRA_RETAIL_EXCHANGE_RATE_VARIABLE_ID", "4"))
        self.serie = int(serie or os.getenv("BCRA_RETAIL_EXCHANGE_RATE_SERIES", "7927"))
        self.base_url = (base_url or os.getenv("BCRA_API_BASE_URL", "https://api.bcra.gob.ar/estadisticas/v4.0")).rstrip("/")
        self.opener = opener or urlopen
        self.sleep = sleep or time.sleep

    def _get(self, path, params=None):
        url = f"{self.base_url}/{path}"
        if params:
            url += "?" + urlencode(params)
        request = Request(url, headers={"Accept": "application/json", "Accept-Language": "es-AR"})
        timeout = float(os.getenv("BCRA_REQUEST_TIMEOUT_SECONDS", "10"))
        for attempt in range(3):
            try:
                with self.opener(request, timeout=timeout) as response:
                    payload = json.load(response, parse_float=Decimal)
                if not isinstance(payload, dict) or payload.get("status") != 200 or not isinstance(payload.get("results"), list):
                    raise BcraClientError("Respuesta BCRA inválida.")
                return payload
            except HTTPError as exc:
                transient = exc.code == 429 or exc.code >= 500
                if not transient or attempt == 2:
                    raise BcraClientError(f"BCRA respondió HTTP {exc.code}.") from exc
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == 2:
                    raise BcraClientError("No se pudo consultar BCRA.") from exc
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise BcraClientError("Respuesta BCRA inválida.") from exc
            logger.warning("event=bcra_request_retry attempt=%s", attempt + 1)
            self.sleep(2 ** attempt)
        raise BcraClientError("No se pudo consultar BCRA.")

    def verificar_variable(self):
        payload = self._get("monetarias", {"idVariable": self.variable_id})
        variable = next((row for row in payload["results"] if row.get("idVariable") == self.variable_id), None)
        if variable is None:
            raise BcraClientError("La variable BCRA configurada no existe.")
        descripcion = str(variable.get("descripcion", "")).lower()
        codigo = variable.get("cdSerie")
        if codigo is not None:
            if str(codigo) != str(self.serie):
                raise BcraClientError("La serie BCRA no coincide con la configuración.")
        else:
            expected = os.getenv(
                "BCRA_EXCHANGE_RATE_DESCRIPTION_TOKENS", "tipo de cambio minorista,vendedor"
            )
            tokens = [part.strip().lower() for part in expected.split(",") if part.strip()]
            if not tokens or not all(token in descripcion for token in tokens):
                raise BcraClientError("La descripción BCRA no coincide con la serie esperada.")
            methodology = self._get(f"metodologia/{self.variable_id}")
            detail = next((row.get("detalle", "") for row in methodology["results"]
                           if row.get("id") == self.variable_id), "")
            expected_methodology = os.getenv("BCRA_EXCHANGE_RATE_METHODOLOGY_TOKENS", "9791")
            methodology_tokens = [part.strip().lower() for part in expected_methodology.split(",")
                                  if part.strip()]
            if not methodology_tokens or not all(token in str(detail).lower()
                                                 for token in methodology_tokens):
                raise BcraClientError("La metodología BCRA no coincide con la serie esperada.")
        return variable

    def consultar_tipo_cambio(self, desde: date, hasta: date) -> list[CotizacionBCRA]:
        if desde > hasta or hasta > date.today():
            raise ValueError("El rango BCRA debe ser válido y no futuro.")
        payload = self._get(f"monetarias/{self.variable_id}",
                            {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "limit": 3000})
        resultset = payload.get("metadata", {}).get("resultset", {})
        if resultset.get("count", 0) > len(payload["results"]) and resultset.get("count", 0) > 3000:
            raise BcraClientError("El rango BCRA excede el límite de resultados.")
        cotizaciones = []
        for row in payload["results"]:
            if row.get("idVariable") != self.variable_id or not isinstance(row.get("detalle"), list):
                raise BcraClientError("Respuesta BCRA incompatible con la variable configurada.")
            for point in row["detalle"]:
                try:
                    fecha = date.fromisoformat(point["fecha"])
                    valor = Decimal(str(point["valor"]))
                except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
                    raise BcraClientError("Cotización BCRA inválida.") from exc
                if not desde <= fecha <= hasta or not valor.is_finite() or valor <= 0:
                    raise BcraClientError("Cotización BCRA fuera de rango o inválida.")
                cotizaciones.append(CotizacionBCRA(fecha, valor, self.variable_id))
        return cotizaciones
