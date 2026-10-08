import unittest
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import NotFoundError, ValidationError
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService
from modules.transferencia.services.adoptante_service import AdoptanteService


class TransferenciaDomainErrorsTestCase(unittest.TestCase):
    def test_adoptante_invalido_identifica_nombre(self):
        for nombre in ("", "22", "Empresa 22", "Empresa-Sur"):
            with self.subTest(nombre=nombre), self.assertRaises(ValidationError) as caught:
                AdoptanteService.create({"nombre": nombre}, 1)
            self.assertIn("nombre", caught.exception.details["fields"])

    def test_relacion_de_adoptantes_indica_selector(self):
        with self.assertRaises(ValidationError) as caught:
            TransferenciaSocioProductivaService.add_adoptantes(1, [], 1)
        self.assertIn("adoptantes_ids", caught.exception.details["fields"])

    def test_campos_editables_tienen_validaciones_estructuradas(self):
        cases = (
            (lambda: TransferenciaSocioProductivaService._validar_texto("", "demandante"), "demandante"),
            (lambda: TransferenciaSocioProductivaService._validar_monto("x"), "monto"),
            (lambda: TransferenciaSocioProductivaService._validar_fecha("2009-12-31", "fecha_inicio"), "fecha_inicio"),
        )
        for validate, field in cases:
            with self.subTest(field=field), self.assertRaises(ValidationError) as caught:
                validate()
            self.assertIn(field, caught.exception.details["fields"])
    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    @staticmethod
    def _headers():
        return {"Authorization": "Bearer fake-token", "Content-Type": "application/json"}

    def _auth(self, rol="GESTOR"):
        return patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": rol})

    def test_adoptante_expone_validacion_tipificada(self):
        with self._auth(), patch("modules.transferencia.controllers.adoptante_controller.AdoptanteService.create", side_effect=ValidationError("Nombre obligatorio")):
            response = self.client.post("/api/v1/transferencia/adoptantes", json={"nombre": "x"}, headers=self._headers())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_historial_adoptante_exige_rol_y_expone_lista(self):
        path = "/api/v1/transferencia/adoptantes/12/historial"
        with self._auth("LECTURA"), patch("modules.transferencia.controllers.adoptante_controller.AdoptanteService.get_historial", return_value=[{"campo": "nombre"}]) as history:
            response = self.client.get(path, headers=self._headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"campo": "nombre"}])
        history.assert_called_once_with(12)
        with self._auth("INVITADO"), patch("modules.transferencia.controllers.adoptante_controller.AdoptanteService.get_historial") as history:
            response = self.client.get(path, headers=self._headers())
        self.assertEqual(response.status_code, 403)
        history.assert_not_called()

    def test_transferencia_expone_recurso_inexistente(self):
        with self._auth("LECTURA"), patch("modules.transferencia.controllers.transferencia_socio_controller.TransferenciaSocioProductivaService.get_by_id", side_effect=NotFoundError("Transferencia no encontrada")):
            response = self.client.get("/api/v1/transferencia/transferencias/1", headers=self._headers())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_transferencia_oculta_error_inesperado(self):
        marker = "mysql://interno password=secreto"
        with self._auth("LECTURA"), patch("modules.transferencia.controllers.transferencia_socio_controller.TransferenciaSocioProductivaService.get_all", side_effect=RuntimeError(marker)):
            response = self.client.get("/api/v1/transferencia/transferencias/", headers=self._headers())
        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))


if __name__ == "__main__":
    unittest.main()
