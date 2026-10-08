import unittest
from unittest.mock import patch

from flask import Flask, request

from modules.grupo.controllers.cargo_controller import CargoController
from modules.shared.controllers.pagination import (
    paginate_query,
    parse_pagination_params,
)


class FakeQuery:
    def __init__(self, items):
        self.items = items
        self.offset_value = 0
        self.limit_value = None

    def count(self):
        return len(self.items)

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        end = None if self.limit_value is None else self.offset_value + self.limit_value
        return self.items[self.offset_value:end]


class PaginationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            PAGINATION_DEFAULT_PER_PAGE=9,
            PAGINATION_MAX_PER_PAGE=20,
        )

    def test_parsea_parametros_con_defaults_del_proyecto(self):
        with self.app.test_request_context("/cargos/?page=2"):
            params = parse_pagination_params(request_args())

        self.assertEqual(
            params,
            {
                "page": 2,
                "per_page": 9,
                "activos": "true",
                "orden": "asc",
            },
        )

    def test_rechaza_per_page_superior_al_maximo(self):
        with self.app.test_request_context("/cargos/?per_page=21"):
            with self.assertRaises(ValueError) as context:
                parse_pagination_params(request_args())

        self.assertIn("per_page no puede superar 20", str(context.exception))

    def test_rechaza_activos_fuera_de_contrato(self):
        with self.app.test_request_context("/cargos/?page=1&activos=si"):
            with self.assertRaises(ValueError) as context:
                parse_pagination_params(request_args())

        self.assertIn("activos debe ser true, false o all", str(context.exception))

    def test_paginate_query_calcula_slice_y_total(self):
        items, total = paginate_query(FakeQuery([1, 2, 3, 4, 5]), page=2, per_page=2)

        self.assertEqual(items, [3, 4])
        self.assertEqual(total, 5)

    def test_cargo_controller_devuelve_contrato_paginado_si_se_solicita(self):
        with self.app.test_request_context(
            "/cargos/?page=2&per_page=9&activos=all&orden=desc"
        ):
            with patch(
                "modules.grupo.controllers.cargo_controller.CargoService.get_page",
                return_value=([{"id": 10, "nombre": "Secretario"}], 19),
            ):
                response, status_code = CargoController.get_all()

        body = response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(body["data"], [{"id": 10, "nombre": "Secretario"}])
        self.assertEqual(
            body["meta"],
            {
                "page": 2,
                "per_page": 9,
                "total": 19,
                "total_pages": 3,
                "activos": "all",
                "orden": "desc",
            },
        )
        self.assertIsNone(body["error"])

    def test_cargo_controller_mantiene_lista_legacy_sin_paginacion(self):
        with self.app.test_request_context("/cargos/?activos=false"):
            with patch(
                "modules.grupo.controllers.cargo_controller.CargoService.get_all",
                return_value=[{"id": 1, "nombre": "Director"}],
            ):
                response, status_code = CargoController.get_all()

        self.assertEqual(status_code, 200)
        self.assertEqual(response.get_json(), [{"id": 1, "nombre": "Director"}])


def request_args():
    return request.args


if __name__ == "__main__":
    unittest.main()
