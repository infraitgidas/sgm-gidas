"""Contrato HTTP BCRA sin llamadas externas."""

import io
import json
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.recursos.clients.bcra_client import BcraClient, BcraClientError  # noqa: E402


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def response(results):
    return Response(json.dumps({"status": 200, "results": results}).encode())


class BcraClientTests(unittest.TestCase):
    def setUp(self):
        self.opener = Mock()
        self.sleep = Mock()
        self.client = BcraClient(opener=self.opener, sleep=self.sleep)

    def test_valid_response_uses_decimal_and_date(self):
        self.opener.return_value = response([{"idVariable": 4, "detalle": [
            {"fecha": "2026-09-24", "valor": 1538.39}]}])
        result = self.client.consultar_tipo_cambio(date(2026, 9, 24), date(2026, 9, 24))
        self.assertEqual(result[0].valor, Decimal("1538.39"))
        self.assertEqual(result[0].fecha, date(2026, 9, 24))
        self.assertIn("desde=2026-09-24", self.opener.call_args.args[0].full_url)

    def test_timeout_and_500_retry(self):
        self.opener.side_effect = [URLError("timeout"), HTTPError("url", 500, "error", {}, None),
                                   response([{"idVariable": 4, "detalle": []}])]
        self.assertEqual(self.client.consultar_tipo_cambio(date(2026, 9, 24), date(2026, 9, 24)), [])
        self.assertEqual(self.opener.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_400_is_not_retried(self):
        self.opener.side_effect = HTTPError("url", 400, "bad request", {}, None)
        with self.assertRaises(BcraClientError):
            self.client.consultar_tipo_cambio(date(2026, 9, 24), date(2026, 9, 24))
        self.assertEqual(self.opener.call_count, 1)

    def test_invalid_json_is_controlled(self):
        self.opener.return_value = Response(b"{")
        with self.assertRaises(BcraClientError):
            self.client.consultar_tipo_cambio(date(2026, 9, 24), date(2026, 9, 24))

    def test_empty_result_is_valid(self):
        self.opener.return_value = response([])
        self.assertEqual(self.client.consultar_tipo_cambio(date(2026, 9, 24), date(2026, 9, 24)), [])

    def test_variable_mismatch_is_rejected(self):
        self.opener.return_value = response([{"idVariable": 4, "cdSerie": 9999,
                                              "descripcion": "Otra variable"}])
        with self.assertRaises(BcraClientError):
            self.client.verificar_variable()

    def test_catalogo_v4_y_metodologia_identifican_b9791(self):
        self.opener.side_effect = [
            response([{"idVariable": 4, "descripcion": "Tipo de cambio minorista (promedio vendedor)"}]),
            response([{"id": 4, "detalle": "Tipo de cambio peso por dólar según Comunicación B 9791"}]),
        ]
        self.assertEqual(self.client.verificar_variable()["idVariable"], 4)
        self.assertIn("metodologia/4", self.opener.call_args.args[0].full_url)

    def test_metodologia_incorrecta_se_rechaza(self):
        self.opener.side_effect = [
            response([{"idVariable": 4, "descripcion": "Tipo de cambio minorista (promedio vendedor)"}]),
            response([{"id": 4, "detalle": "Otra metodología"}]),
        ]
        with self.assertRaises(BcraClientError):
            self.client.verificar_variable()

    def test_otra_serie_puede_configurarse_por_descripcion(self):
        self.opener.side_effect = [
            response([{"idVariable": 5, "descripcion": "Tipo de Cambio Mayorista Referencia"}]),
            response([{"id": 5, "detalle": "Comunicación A 3500"}]),
        ]
        with patch.dict("os.environ", {"BCRA_EXCHANGE_RATE_DESCRIPTION_TOKENS": "mayorista",
                                    "BCRA_EXCHANGE_RATE_METHODOLOGY_TOKENS": "3500"}):
            client = BcraClient(variable_id=5, serie=9999, opener=self.opener, sleep=self.sleep)
            self.assertEqual(client.verificar_variable()["idVariable"], 5)


if __name__ == "__main__":
    unittest.main()
