import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import ValidationError


class ExportacionesSeguridadTestCase(unittest.TestCase):

    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _headers(self):
        return {
            "Authorization": "Bearer fake-token",
            "Content-Type": "application/json",
        }

    def _auth_patch(self, rol="GESTOR"):
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "2", "rol": rol},
        )

    def test_exportar_grupo_sin_grupo_activo_devuelve_not_found_seguro(self):
        with self._auth_patch(), patch(
            "modules.grupo.controllers.grupo_controller.obtener_grupo_utn",
            return_value=None,
        ), patch(
            "modules.grupo.controllers.grupo_controller.ExportService.generar_excel_grupo"
        ) as mock_generar:
            response = self.client.get(
                "/api/v1/grupo/grupo-utn/exportar-excel",
                headers=self._headers(),
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertNotIn("traceback", body)
        mock_generar.assert_not_called()

    def test_exportar_grupo_error_interno_no_expone_detalle(self):
        with self._auth_patch(), patch(
            "modules.grupo.controllers.grupo_controller.obtener_grupo_utn",
            return_value=SimpleNamespace(id=7),
        ), patch(
            "modules.grupo.controllers.grupo_controller.ExportService.generar_excel_grupo",
            side_effect=RuntimeError("ruta interna sensible"),
        ):
            response = self.client.get(
                "/api/v1/grupo/grupo-utn/exportar-excel",
                headers=self._headers(),
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("ruta interna sensible", body["error"]["message"])
        self.assertNotIn("traceback", body)

    def test_exportar_memoria_error_controlado_no_expone_traceback(self):
        with self._auth_patch(), patch(
            "modules.memorias.controllers.memoria_controller.ExportService.generar_excel_memoria",
            side_effect=ValidationError("No se puede exportar esta memoria"),
        ):
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/exportar-excel",
                headers=self._headers(),
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertNotIn("detalle interno sensible", body["error"]["message"])
        self.assertNotIn("traceback", body)


if __name__ == "__main__":
    unittest.main()
