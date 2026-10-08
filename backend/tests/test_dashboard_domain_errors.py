import unittest
from unittest.mock import patch

from app import create_app


class DashboardDomainErrorsTestCase(unittest.TestCase):
    def setUp(self):
        # These tests exercise error responses, independently of tenant setup.
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _auth(self):
        return patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "LECTURA"})

    @staticmethod
    def _headers():
        return {"Authorization": "Bearer fake-token"}

    def test_parametro_invalido_es_error_tipificado(self):
        with self._auth():
            response = self.client.get("/api/v1/dashboards/resumen?anios=0", headers=self._headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_dashboard_oculta_error_inesperado(self):
        marker = "sql interno password=secreto"
        with self._auth(), patch("modules.dashboard.controllers.dashboard_controller.DashboardService.get_resumen", side_effect=RuntimeError(marker)):
            response = self.client.get("/api/v1/dashboards/resumen", headers=self._headers())
        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))


if __name__ == "__main__":
    unittest.main()
