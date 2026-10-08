import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.personal.services.personal_service import _validar_nombre
from modules.personal.services.investigador_service import _validar_nombre as _validar_nombre_investigador
from modules.personal.services.becario_service import _validar_nombre as _validar_nombre_becario, _validar_proyectos_ids, _sincronizar_becas


class PersonalDomainErrorsTestCase(unittest.TestCase):

    def test_variantes_de_personal_identifican_nombre_y_proyectos(self):
        for validar in (_validar_nombre_investigador, _validar_nombre_becario):
            with self.assertRaises(ValidationError) as caught:
                validar("")
            self.assertIn("nombre_apellido", caught.exception.details["fields"])
        with self.assertRaises(ValidationError) as caught:
            _validar_proyectos_ids([1, 1])
        self.assertIn("proyectos", caught.exception.details["fields"])

    def test_beca_invalida_identifica_selector(self):
        with self.app.app_context(), patch("modules.personal.services.becario_service.db.session.get", return_value=SimpleNamespace(deleted_at=None)), self.assertRaises(ValidationError) as caught:
            _sincronizar_becas(None, [{"beca_id": 1, "fecha_inicio": "invalida"}], 1)
        self.assertIn("becas", caught.exception.details["fields"])

    def test_nombre_invalido_indica_campo_editable(self):
        for nombre in (None, "", "22", "Ana 22", "Ana-María", "Ana_", "x" * 121):
            with self.subTest(nombre=nombre), self.assertRaises(ValidationError) as caught:
                _validar_nombre(nombre)
            self.assertIn("nombre_apellido", caught.exception.details["fields"])

    def test_nombres_de_personas_solo_admiten_letras_y_espacios(self):
        for validar in (_validar_nombre, _validar_nombre_investigador, _validar_nombre_becario):
            for invalido in ("22", "Ana 22", "Ana-María", "Ana!", "Ana\tMaría"):
                with self.subTest(validar=validar.__module__, nombre=invalido), self.assertRaises(ValidationError) as caught:
                    validar(invalido)
                self.assertIn("nombre_apellido", caught.exception.details["fields"])
            self.assertEqual(validar("Ana María"), "Ana María")

    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    @staticmethod
    def _headers():
        return {"Authorization": "Bearer fake-token", "Content-Type": "application/json"}

    def _auth(self, rol="GESTOR"):
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": rol},
        )

    def test_tipo_personal_expone_validacion_tipificada(self):
        with self._auth(), patch(
            "modules.personal.controllers.tipo_personal_controller.crear_tipo_personal",
            side_effect=ValidationError("El nombre es obligatorio"),
        ):
            response = self.client.post(
                "/api/v1/personal/tipo-personal/", json={}, headers=self._headers()
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_tipo_formacion_expone_not_found_tipificado(self):
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.tipo_formacion_controller."
            "obtener_tipo_formacion_por_id",
            side_effect=NotFoundError("Tipo de formacion no encontrado"),
        ):
            response = self.client.get(
                "/api/v1/personal/tipo-formacion/1", headers=self._headers()
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_tipo_dedicacion_expone_conflicto_tipificado(self):
        with self._auth(), patch(
            "modules.personal.controllers.tipo_dedicacion_controller."
            "eliminar_tipo_dedicacion",
            side_effect=ConflictError("El tipo esta asociado"),
        ):
            response = self.client.delete(
                "/api/v1/personal/tipo-dedicacion/1", headers=self._headers()
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "CONFLICT")

    def test_catalogo_personal_oculta_error_inesperado(self):
        marker = "postgresql password=secreto"
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.tipo_formacion_controller."
            "listar_tipos_formacion",
            side_effect=RuntimeError(marker),
        ):
            response = self.client.get(
                "/api/v1/personal/tipo-formacion/", headers=self._headers()
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))

    def test_investigador_expone_not_found_tipificado(self):
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.investigador_controller."
            "obtener_investigador_por_id",
            side_effect=NotFoundError("Investigador no encontrado"),
        ):
            response = self.client.get(
                "/api/v1/personal/investigadores/1", headers=self._headers()
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_becario_expone_conflicto_tipificado(self):
        with self._auth(), patch(
            "modules.personal.controllers.becario_controller.eliminar_becario",
            side_effect=ConflictError("El becario ya esta eliminado"),
        ):
            response = self.client.delete(
                "/api/v1/personal/becarios/1", headers=self._headers()
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "CONFLICT")

    def test_personal_oculta_error_inesperado(self):
        marker = "documento=12345678 password=secreto"
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.personal_controller.listar_personal",
            side_effect=RuntimeError(marker),
        ):
            response = self.client.get("/api/v1/personal", headers=self._headers())

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))

    def test_personal_completo_oculta_error_inesperado(self):
        marker = "correo=privado@example.com"
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.personal_completo_controller."
            "listar_personal_completo",
            side_effect=RuntimeError(marker),
        ):
            response = self.client.get(
                "/api/v1/personal/all", headers=self._headers()
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))

    def test_personal_no_encontrado_usa_contrato_compartido(self):
        with self._auth("LECTURA"), patch(
            "modules.personal.controllers.personal_controller."
            "obtener_personal_por_tipo",
            return_value=None,
        ):
            response = self.client.get(
                "/api/v1/personal/investigador/999",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
