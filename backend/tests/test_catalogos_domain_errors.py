import unittest
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import NotFoundError, ValidationError


class CatalogosDomainErrorsTestCase(unittest.TestCase):
    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _auth(self, rol="GESTOR"):
        return patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": rol})

    @staticmethod
    def _headers():
        return {"Authorization": "Bearer fake-token", "Content-Type": "application/json"}

    def test_categoria_expone_validacion(self):
        with self._auth(), patch("modules.catalogos.controllers.categoria_utn_controller.crear_categoria_utn", side_effect=ValidationError("Nombre obligatorio")):
            response = self.client.post("/api/v1/catalogos/categoria-utn/", json={"nombre": "x"}, headers=self._headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_fuente_expone_no_encontrado(self):
        with self._auth("LECTURA"), patch("modules.catalogos.controllers.fuente_financiamiento_controller.obtener_fuente_financiamiento_por_id", side_effect=NotFoundError("Fuente no encontrada")):
            response = self.client.get("/api/v1/catalogos/fuente-financiamiento/1", headers=self._headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_catalogo_oculta_error_inesperado(self):
        marker = "driver interno password=secreto"
        with self._auth("LECTURA"), patch("modules.catalogos.controllers.categoria_utn_controller.listar_categorias_utn", side_effect=RuntimeError(marker)):
            response = self.client.get("/api/v1/catalogos/categoria-utn/", headers=self._headers())
        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))


if __name__ == "__main__":
    unittest.main()
