import unittest
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import ValidationError
from modules.grupo.services.grupo_service import crear_grupo_utn
from modules.grupo.services.programa_actividades_service import _validar_anio, _validar_descripcion


class GrupoDomainErrorsTestCase(unittest.TestCase):

    def test_uct_identifica_el_campo_obligatorio_antes_de_persistir(self):
        with self.app.app_context(), patch("modules.grupo.services.grupo_service.GrupoInvestigacionUtn.query") as query, patch("modules.grupo.services.grupo_service.db.session.add") as add:
            query.filter.return_value.first.return_value = None
            with self.assertRaises(ValidationError) as caught:
                crear_grupo_utn({}, 1)
            add.assert_not_called()
            self.assertEqual(caught.exception.details, {})

            with self.assertRaises(ValidationError) as caught:
                crear_grupo_utn({"nombre_unidad_academica": ""}, 1)
            self.assertIn("nombre_unidad_academica", caught.exception.details["fields"])
            add.assert_not_called()

    def test_planificacion_identifica_descripcion_y_anio(self):
        for validate, value, field in ((_validar_descripcion, "", "descripcion"), (_validar_anio, 1999, "anio")):
            with self.subTest(field=field), self.assertRaises(ValidationError) as caught:
                validate(value)
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
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": rol},
        )

    def test_opciones_uct_respeta_roles_y_contrato(self):
        for rol, status in (("ADMIN", 200), ("GESTOR", 200), ("LECTURA", 200), ("LECTOR", 403)):
            with self.subTest(rol=rol), self._auth(rol), patch(
                "modules.grupo.controllers.grupo_controller.listar_grupos_utn_activos",
                return_value=[{"id": 3, "nombre": "GIDAS"}],
            ):
                response = self.client.get(
                    "/api/v1/grupo/grupo-utn/opciones", headers=self._headers()
                )
            self.assertEqual(response.status_code, status)
            if status == 200:
                self.assertEqual(response.get_json(), [{"id": 3, "nombre": "GIDAS"}])

    def test_cargo_expone_validacion_tipificada(self):
        with self._auth(), patch(
            "modules.grupo.controllers.cargo_controller.CargoService.create",
            side_effect=ValidationError("El nombre es obligatorio"),
        ):
            response = self.client.post(
                "/api/v1/grupo/cargos/", json={}, headers=self._headers()
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_cargo_oculta_error_inesperado(self):
        marker = "ruta interna password=secreto"
        with self._auth("LECTURA"), patch(
            "modules.grupo.controllers.cargo_controller.CargoService.get_all",
            side_effect=RuntimeError(marker),
        ):
            response = self.client.get(
                "/api/v1/grupo/cargos/", headers=self._headers()
            )
        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))

    def test_grupo_no_configurado_usa_contrato_compartido(self):
        with self._auth("LECTURA"), patch(
            "modules.grupo.controllers.grupo_controller.obtener_grupo_utn",
            return_value=None,
        ):
            response = self.client.get(
                "/api/v1/grupo/grupo-utn/",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "NOT_FOUND")

    def test_historial_grupo_respeta_roles_y_contrato(self):
        for rol, status in (("ADMIN", 200), ("GESTOR", 200), ("LECTURA", 200), ("LECTOR", 403)):
            with self.subTest(rol=rol), self._auth(rol), patch(
                "modules.grupo.controllers.grupo_controller.obtener_historial_grupo_utn",
                return_value=[{"id": 1, "campo": "mail"}],
            ):
                response = self.client.get(
                    "/api/v1/grupo/grupo-utn/3/historial",
                    headers=self._headers(),
                )
            self.assertEqual(response.status_code, status)
            if status == 200:
                self.assertEqual(response.get_json(), [{"id": 1, "campo": "mail"}])


if __name__ == "__main__":
    unittest.main()
