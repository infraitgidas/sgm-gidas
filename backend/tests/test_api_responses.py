import unittest

from flask import Flask, g

from modules.shared.controllers.responses import (
    error_response,
    exception_response,
    paginated_response,
    success_response,
)
from modules.shared.exceptions import NotFoundError, ValidationError
from modules.shared.routes.status import health_bp


class ApiResponsesTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)

    def test_success_response_usa_contrato_base(self):
        with self.app.app_context():
            response, status_code = success_response({"status": "ok"})

        self.assertEqual(status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "data": {"status": "ok"},
                "meta": {},
                "error": None,
            },
        )

    def test_paginated_response_calcula_metadata(self):
        with self.app.app_context():
            response, status_code = paginated_response(
                data=[{"id": 1}],
                page=2,
                per_page=9,
                total=20,
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(response.get_json()["data"], [{"id": 1}])
        self.assertEqual(
            response.get_json()["meta"],
            {
                "page": 2,
                "per_page": 9,
                "total": 20,
                "total_pages": 3,
            },
        )
        self.assertIsNone(response.get_json()["error"])

    def test_error_response_usa_mensaje_seguro_por_codigo(self):
        with self.app.app_context():
            response, status_code = error_response(
                "VALIDATION_ERROR",
                details={"campo": "nombre"},
                status_code=422,
            )

        self.assertEqual(status_code, 422)
        self.assertIsNone(response.get_json()["data"])
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.get_json()["error"]["details"], {})
        self.assertIn("Verifique los datos", response.get_json()["error"]["message"])

    def test_health_endpoint_usa_contrato_uniforme(self):
        self.app.register_blueprint(health_bp)

        response = self.app.test_client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "data": {"status": "ok"},
                "meta": {},
                "error": None,
            },
        )

    def test_exception_response_expone_solo_error_de_dominio(self):
        with self.app.test_request_context():
            response, status_code = exception_response(
                ValidationError("El periodo es obligatorio", details={"campo": "periodo"}),
                operation="crear memoria",
            )

        self.assertEqual(status_code, 400)
        self.assertEqual(response.get_json()["error"], {
            "code": "VALIDATION_ERROR",
            "message": "El periodo es obligatorio",
            "details": {},
        })

    def test_exception_response_respeta_estado_not_found(self):
        with self.app.test_request_context():
            response, status_code = exception_response(
                NotFoundError("Memoria no encontrada"),
                operation="consultar memoria",
            )

        self.assertEqual(status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_exception_response_oculta_error_inesperado_y_agrega_request_id(self):
        with self.app.test_request_context():
            g.request_id = "req-seguro-123"
            response, status_code = exception_response(
                RuntimeError("postgresql://usuario:secreto@db/interna"),
                operation="consultar memoria",
            )

        body = response.get_json()
        self.assertEqual(status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertEqual(body["error"]["details"], {"request_id": "req-seguro-123"})
        self.assertNotIn("secreto", str(body))


if __name__ == "__main__":
    unittest.main()
