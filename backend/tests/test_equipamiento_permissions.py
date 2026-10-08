import unittest
from unittest.mock import patch

from app import create_app


class EquipamientoPermissionsTestCase(unittest.TestCase):

    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer fake-token"}

    def _auth(self, role):
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": role},
        )

    def test_admin_puede_eliminar_equipamiento(self):
        with self._auth("ADMIN"), patch(
            "modules.recursos.controllers.equipamiento_controller."
            "EquipamientoService.delete",
            return_value={"message": "Equipamiento eliminado correctamente"},
        ) as delete:
            response = self.client.delete(
                "/api/v1/recursos/equipamiento/1",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        delete.assert_called_once_with(1, 7)

    def test_gestor_puede_eliminar_equipamiento(self):
        with self._auth("GESTOR"), patch(
            "modules.recursos.controllers.equipamiento_controller."
            "EquipamientoService.delete",
            return_value={"message": "Equipamiento eliminado correctamente"},
        ) as delete:
            response = self.client.delete(
                "/api/v1/recursos/equipamiento/1",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        delete.assert_called_once_with(1, 7)

    def test_lectura_no_puede_eliminar_equipamiento(self):
        with self._auth("LECTURA"), patch(
            "modules.recursos.controllers.equipamiento_controller."
            "EquipamientoService.delete"
        ) as delete:
            response = self.client.delete(
                "/api/v1/recursos/equipamiento/1",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "FORBIDDEN")
        delete.assert_not_called()

    def test_rol_lector_heredado_no_elude_los_permisos(self):
        with self._auth("LECTOR"), patch(
            "modules.recursos.controllers.equipamiento_controller."
            "EquipamientoService.delete"
        ) as delete:
            response = self.client.delete(
                "/api/v1/recursos/equipamiento/1",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "FORBIDDEN")
        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
