import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import create_app
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService


class ActividadDocenciaActionsTestCase(unittest.TestCase):

    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    @staticmethod
    def _headers():
        return {
            "Authorization": "Bearer fake-token",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _auth():
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": "GESTOR"},
        )

    def test_editar_actividad_responde_y_envia_usuario_actual(self):
        resultado = {"id": 4, "curso": "Curso actualizado"}
        with self._auth(), patch(
            "modules.produccion.controllers.actividad_docencia_controller."
            "ActividadDocenciaService.update",
            return_value=resultado,
        ) as update:
            response = self.client.put(
                "/api/v1/produccion/actividades-docencia/4",
                headers=self._headers(),
                json={"curso": "Curso actualizado"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), resultado)
        update.assert_called_once_with(
            4,
            {"curso": "Curso actualizado"},
            user_id=7,
        )

    def test_eliminar_actividad_responde_y_envia_usuario_actual(self):
        resultado = {"message": "Actividad de docencia eliminada correctamente"}
        with self._auth(), patch(
            "modules.produccion.controllers.actividad_docencia_controller."
            "ActividadDocenciaService.delete",
            return_value=resultado,
        ) as delete:
            response = self.client.delete(
                "/api/v1/produccion/actividades-docencia/4",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), resultado)
        delete.assert_called_once_with(4, user_id=7)

    def test_eliminar_actividad_aplica_baja_logica_y_confirma(self):
        actividad = SimpleNamespace(soft_delete=Mock())
        with patch.object(
            ActividadDocenciaService,
            "_obtener_actividad",
            return_value=actividad,
        ), patch(
            "modules.produccion.services.actividad_docencia_service.db.session.commit"
        ) as commit:
            resultado = ActividadDocenciaService.delete(4, user_id=7)

        actividad.soft_delete.assert_called_once_with(7)
        commit.assert_called_once_with()
        self.assertEqual(
            resultado,
            {"message": "Actividad de docencia eliminada correctamente"},
        )


if __name__ == "__main__":
    unittest.main()
