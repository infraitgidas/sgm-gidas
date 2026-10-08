import unittest

from flask import abort

from app import create_app
from modules.shared.exceptions import ValidationError, NotFoundError, ConflictError, ForbiddenError
from modules.shared.services.error_messages import public_message


class ErrorHandlersTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)

        @self.app.get("/_test/http-error/<int:status_code>")
        def raise_http_error(status_code):
            abort(status_code, description="detalle interno no confiable")

        @self.app.get("/_test/unexpected-error")
        def raise_unexpected_error():
            raise RuntimeError("password=secreto-no-debe-reflejarse")

        @self.app.get("/_test/domain-error/<kind>")
        def raise_domain_error(kind):
            errors = {
                "validation": ValidationError("codigo_proyecto debe ser alfanumerico", details={"fields": {
                    "codigo_proyecto": "El código del proyecto debe ser alfanumérico",
                }}),
                "without_field": ValidationError("La fecha debe ser posterior."),
                "related": ValidationError("Seleccione un investigador disponible.", details={"fields": {
                    "id_investigador": "Seleccione un investigador disponible.",
                }}),
                "missing": NotFoundError("Recurso no encontrado."),
                "conflict": ConflictError("Revise el estado e intente nuevamente."),
                "forbidden": ForbiddenError("No tiene permisos para realizar esta acción."),
            }
            raise errors[kind]

        self.client = self.app.test_client()

    def _assert_safe_error(self, response, status_code, code):
        payload = response.get_json()
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(payload["data"], None)
        self.assertEqual(payload["error"]["code"], code)
        self.assertEqual(
            payload["error"]["details"]["request_id"],
            "error-handler-test",
        )
        self.assertEqual(response.headers["X-Request-ID"], "error-handler-test")
        self.assertNotIn("detalle interno", body)
        self.assertNotIn("secreto-no-debe-reflejarse", body)
        self.assertNotIn("traceback", body.lower())

    def test_errores_de_dominio_globales_y_campos_publicos(self):
        cases = {"validation": (400, "VALIDATION_ERROR"), "without_field": (400, "VALIDATION_ERROR"), "related": (400, "VALIDATION_ERROR"),
                 "missing": (404, "NOT_FOUND"), "conflict": (409, "CONFLICT"), "forbidden": (403, "FORBIDDEN")}
        for kind, (status, code) in cases.items():
            with self.subTest(kind=kind):
                response = self.client.get(f"/_test/domain-error/{kind}", headers={"X-Request-ID": "error-handler-test"})
                self._assert_safe_error(response, status, code)
                if kind == "validation":
                    message = response.get_json()["error"]["details"]["fields"]["codigo_proyecto"]
                    self.assertIn("código del proyecto", message)
                    self.assertNotIn("codigo_proyecto", message)
                if kind == "related":
                    self.assertIn("id_investigador", response.get_json()["error"]["details"]["fields"])
                if kind == "without_field":
                    self.assertNotIn("fields", response.get_json()["error"]["details"])

    def test_mensaje_publico_no_expone_detalle_interno(self):
        self.assertEqual(public_message("columna_interna inválida", "Intente nuevamente."), "Intente nuevamente.")
        self.assertEqual(public_message("Seleccione esta beca", "fallback"), "Seleccione esta beca")

    def test_handlers_http_requeridos_usan_contrato_seguro(self):
        expected_codes = {
            400: "VALIDATION_ERROR",
            401: "AUTH_REQUIRED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "REQUEST_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
        }

        for status_code, code in expected_codes.items():
            with self.subTest(status_code=status_code):
                response = self.client.get(
                    f"/_test/http-error/{status_code}",
                    headers={"X-Request-ID": "error-handler-test"},
                )
                self._assert_safe_error(response, status_code, code)

    def test_error_http_no_mapeado_no_refleja_descripcion(self):
        response = self.client.get(
            "/_test/http-error/405",
            headers={"X-Request-ID": "error-handler-test"},
        )

        self._assert_safe_error(response, 405, "HTTP_ERROR")

    def test_excepcion_inesperada_responde_500_seguro(self):
        response = self.client.get(
            "/_test/unexpected-error",
            headers={"X-Request-ID": "error-handler-test"},
        )

        self._assert_safe_error(response, 500, "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
