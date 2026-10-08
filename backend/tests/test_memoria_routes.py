import unittest
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import ValidationError


class MemoriaRoutesTestCase(unittest.TestCase):

    def setUp(self):
        # Route/RBAC contract tests use fake tokens and mocked services.
        # Tenant authorization with real memberships is covered separately.
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _headers(self, token="fake-token"):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def test_get_all_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "1", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_all",
            return_value=[]
        ) as mock_get_all:
            response = self.client.get("/api/v1/memorias", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])
        mock_get_all.assert_called_once_with("true")

    def test_get_all_paginado_usa_service_limitado(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "1", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_page",
            return_value=([{"id": 2}], 12)
        ) as mock_page, patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_all"
        ) as mock_all:
            response = self.client.get(
                "/api/v1/memorias?page=2&per_page=3", headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], [{"id": 2}])
        self.assertEqual(response.get_json()["meta"]["total_pages"], 4)
        mock_page.assert_called_once_with(page=2, per_page=3, activos="true", orden="asc")
        mock_all.assert_not_called()

    def test_get_by_id_sin_token_devuelve_401(self):
        response = self.client.get("/api/v1/memorias/1")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "AUTH_REQUIRED")

    def test_exportar_excel_error_no_expone_traceback(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "2", "rol": "GESTOR"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.ExportService.generar_excel_memoria",
            side_effect=RuntimeError("postgresql://usuario:secreto@db/interna")
        ):
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/exportar-excel",
                headers=self._headers()
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("traceback", body)
        self.assertNotIn("detalle interno sensible", body["error"]["message"])

    def test_create_expone_validacion_tipificada(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "3", "rol": "ADMIN"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.create",
            side_effect=ValidationError("El periodo es obligatorio")
        ):
            response = self.client.post(
                "/api/v1/memorias",
                json={},
                headers=self._headers(),
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["message"], "El periodo es obligatorio")

    def test_get_by_id_oculta_error_inesperado(self):
        marker = "postgresql://usuario:secreto@db/interna"
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "4", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_by_id",
            side_effect=RuntimeError(marker)
        ):
            response = self.client.get(
                "/api/v1/memorias/1",
                headers=self._headers(),
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn(marker, str(body))

    def test_get_snapshot_investigadores_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "9", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_investigadores_snapshot",
            return_value=[{"investigador_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/investigadores",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"investigador_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_becarios_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "10", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_becarios_snapshot",
            return_value=[{"becario_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/becarios",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"becario_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_personal_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "11", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_personal_snapshot",
            return_value=[{"personal_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/personal",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"personal_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_proyectos_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "12", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_proyectos_snapshot",
            return_value=[{"proyecto_investigacion_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/proyectos",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"proyecto_investigacion_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_actividades_docencia_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "13", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_actividades_docencia_snapshot",
            return_value=[{"actividad_docencia_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/actividades-docencia",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"actividad_docencia_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_participaciones_relevantes_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "14", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_participaciones_relevantes_snapshot",
            return_value=[{"participacion_relevante_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/participaciones-relevantes",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"participacion_relevante_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_documentacion_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "15", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_documentacion_snapshot",
            return_value=[{"documentacion_bibliografica_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/documentacion-bibliografica",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"documentacion_bibliografica_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_equipamiento_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "16", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_equipamiento_snapshot",
            return_value=[{"equipamiento_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/equipamiento",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"equipamiento_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_erogaciones_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "17", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_erogaciones_snapshot",
            return_value=[{"erogacion_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/erogaciones",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"erogacion_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_transferencias_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "18", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_transferencias_snapshot",
            return_value=[{"transferencia_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/transferencias",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"transferencia_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_trabajos_reunion_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "19", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_trabajos_reunion_snapshot",
            return_value=[{"trabajo_reunion_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/trabajos-reunion-cientifica",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"trabajo_reunion_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_trabajos_revista_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "20", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_trabajos_revista_snapshot",
            return_value=[{"trabajo_revista_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/trabajos-revistas",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"trabajo_revista_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_distinciones_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "21", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_distinciones_snapshot",
            return_value=[{"distincion_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/distinciones",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"distincion_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_registros_propiedad_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "22", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_registros_propiedad_snapshot",
            return_value=[{"registro_propiedad_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/registros-propiedad",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"registro_propiedad_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_articulos_divulgacion_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "23", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_articulos_divulgacion_snapshot",
            return_value=[{"articulo_divulgacion_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/articulos-divulgacion",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"articulo_divulgacion_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_get_snapshot_visitas_con_rol_lectura_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "24", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.get_visitas_snapshot",
            return_value=[{"visita_academica_id": 1}]
        ) as mock_get_snapshot:
            response = self.client.get(
                "/api/v1/memorias/1/versiones/2/visitas-academicas",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"visita_academica_id": 1}])
        mock_get_snapshot.assert_called_once_with(1, 2)

    def test_post_con_rol_lectura_devuelve_403(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "2", "rol": "LECTURA"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.create"
        ) as mock_create:
            response = self.client.post(
                "/api/v1/memorias",
                json={
                    "periodo_inicio": "2026-01-01",
                    "periodo_fin": "2026-12-31"
                },
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "FORBIDDEN")
        mock_create.assert_not_called()

    def test_post_con_rol_admin_devuelve_201(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "3", "rol": "ADMIN"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.create",
            return_value={"id": 1}
        ) as mock_create:
            payload = {
                "periodo_inicio": "2026-01-01",
                "periodo_fin": "2026-12-31"
            }
            response = self.client.post(
                "/api/v1/memorias",
                json=payload,
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"id": 1})
        mock_create.assert_called_once_with(payload, 3)

    def test_put_estado_con_rol_admin_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "4", "rol": "ADMIN"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.change_status",
            return_value={"id": 1, "version_actual": {"estado": "cerrada"}}
        ) as mock_change_status:
            payload = {"estado": "cerrada"}
            response = self.client.put(
                "/api/v1/memorias/1/estado",
                json=payload,
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"id": 1, "version_actual": {"estado": "cerrada"}}
        )
        mock_change_status.assert_called_once_with(1, payload, 4)

    def test_delete_con_rol_gestor_devuelve_403(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "5", "rol": "GESTOR"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.delete"
        ) as mock_delete:
            response = self.client.delete(
                "/api/v1/memorias/1",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "FORBIDDEN")
        mock_delete.assert_not_called()

    def test_delete_con_rol_admin_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "6", "rol": "ADMIN"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.delete",
            return_value={"message": "Memoria eliminada correctamente"}
        ) as mock_delete:
            response = self.client.delete(
                "/api/v1/memorias/1",
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"message": "Memoria eliminada correctamente"}
        )
        mock_delete.assert_called_once_with(1, 6)

    def test_reopen_con_rol_gestor_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": "GESTOR"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.reopen",
            return_value={"id": 1, "version_actual": {"numero_version": 2}}
        ) as mock_reopen:
            response = self.client.put(
                "/api/v1/memorias/1/reabrir",
                json={"fecha_apertura": "2026-03-05"},
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        mock_reopen.assert_called_once_with(1, 7, {"fecha_apertura": "2026-03-05"})

    def test_reopen_con_rol_admin_devuelve_200(self):
        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "8", "rol": "ADMIN"}
        ), patch(
            "modules.memorias.controllers.memoria_controller.MemoriaService.reopen",
            return_value={"id": 1, "version_actual": {"numero_version": 2}}
        ) as mock_reopen:
            payload = {"fecha_apertura": "2026-03-05"}
            response = self.client.put(
                "/api/v1/memorias/1/reabrir",
                json=payload,
                headers=self._headers()
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"id": 1, "version_actual": {"numero_version": 2}}
        )
        mock_reopen.assert_called_once_with(1, 8, payload)


if __name__ == "__main__":
    unittest.main()
