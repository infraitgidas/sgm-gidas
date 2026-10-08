import unittest
from unittest.mock import patch

from app import create_app
from modules.shared.exceptions import ConflictError


class MovimientoFinancieroApiTestCase(unittest.TestCase):
    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.client = create_app().test_client()
        self.base = "/api/v1/recursos/movimientos"

    @staticmethod
    def _headers():
        return {"Authorization": "Bearer fake-token"}

    @staticmethod
    def _auth(rol):
        return patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "7", "rol": rol},
        )

    def test_lectura_ve_listado_y_no_puede_crear(self):
        with self._auth("LECTURA"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "MovimientoFinancieroService.get_all", return_value=[],
        ):
            listado = self.client.get(f"{self.base}/", headers=self._headers())
            alta = self.client.post(f"{self.base}/", json={}, headers=self._headers())
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(alta.status_code, 403)

    def test_lector_puede_consultar_saldos_por_fuente(self):
        resultado = [{
            "fuente_id": 3, "fuente_nombre": "UTN",
            "total_ingresos": "100.25", "total_egresos": "25.00",
            "saldo_disponible": "75.25", "cantidad_movimientos": 2,
        }]
        with self._auth("LECTURA"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "SaldoFinancieroService.saldos_por_fuente", return_value=resultado,
        ) as consulta:
            respuesta = self.client.get(
                f"{self.base}/grupos/7/saldos-por-fuente", headers=self._headers(),
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), resultado)
        consulta.assert_called_once_with(7)

    def test_lector_consulta_cotizacion_vigente_y_no_puede_escribir(self):
        class Cotizacion:
            def serialize(self):
                return {"fecha_cotizacion": "2026-09-25", "valor": "1538.390000"}

        with self._auth("LECTURA"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "TipoCambioService.obtener_vigente_para_fecha", return_value=Cotizacion(),
        ) as buscar:
            respuesta = self.client.get(
                f"{self.base}/cotizacion?fecha=2026-09-26", headers=self._headers(),
            )
            alta = self.client.post(f"{self.base}/", json={}, headers=self._headers())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["fecha_cotizacion"], "2026-09-25")
        self.assertEqual(alta.status_code, 403)
        self.assertEqual(buscar.call_args.args[0].isoformat(), "2026-09-26")

    def test_lector_puede_consultar_equipamiento_disponible(self):
        resultado = [{"id": 4, "denominacion": "Microscopio", "monto_invertido": "75.50"}]
        with self._auth("LECTURA"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "MovimientoFinancieroService.equipamientos_disponibles", return_value=resultado,
        ) as consulta:
            respuesta = self.client.get(
                f"{self.base}/grupos/7/equipamientos-disponibles?movimiento_id=9",
                headers=self._headers(),
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), resultado)
        consulta.assert_called_once_with(7, 9)

    def test_gestor_puede_crear_y_conflicto_financiero_es_409(self):
        with self._auth("GESTOR"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "MovimientoFinancieroService.create",
            return_value={"id": 1, "numero_movimiento": 1},
        ):
            creado = self.client.post(f"{self.base}/", json={"monto": "1.00"}, headers=self._headers())
        self.assertEqual(creado.status_code, 201)
        self.assertEqual(creado.get_json()["numero_movimiento"], 1)

        with self._auth("GESTOR"), patch(
            "modules.recursos.controllers.movimiento_financiero_controller."
            "MovimientoFinancieroService.delete",
            side_effect=ConflictError("Saldo insuficiente"),
        ):
            rechazado = self.client.delete(f"{self.base}/1", headers=self._headers())
        self.assertEqual(rechazado.status_code, 409)
        self.assertEqual(rechazado.get_json()["error"]["code"], "CONFLICT")

    def test_edicion_baja_detalle_e_historial_exponen_contrato_nuevo(self):
        service_path = (
            "modules.recursos.controllers.movimiento_financiero_controller."
            "MovimientoFinancieroService"
        )
        with self._auth("GESTOR"), patch(f"{service_path}.get_by_id", return_value={
            "id": 1, "tipo_movimiento": "INGRESO", "monto": "100.00",
        }), patch(f"{service_path}.get_historial", return_value=[{
            "id": 7, "campo": "monto", "valor_anterior": "90.00", "valor_nuevo": "100.00",
        }]), patch(f"{service_path}.update", return_value={
            "id": 1, "monto": "100.00", "tipo_movimiento": "INGRESO",
        }) as update, patch(f"{service_path}.delete", return_value={
            "message": "Movimiento eliminado correctamente.",
        }) as delete:
            detalle = self.client.get(f"{self.base}/1", headers=self._headers())
            historial = self.client.get(f"{self.base}/1/historial", headers=self._headers())
            editado = self.client.put(f"{self.base}/1", json={"monto": "100.00"}, headers=self._headers())
            eliminado = self.client.delete(f"{self.base}/1", headers=self._headers())
        self.assertEqual([detalle.status_code, historial.status_code, editado.status_code, eliminado.status_code], [200, 200, 200, 200])
        self.assertEqual(historial.get_json()[0]["campo"], "monto")
        self.assertEqual(editado.get_json()["tipo_movimiento"], "INGRESO")
        self.assertEqual(update.call_args.args[:2], (1, {"monto": "100.00"}))
        self.assertEqual(delete.call_args.args[0], 1)

    def test_lector_no_puede_editar_ni_eliminar(self):
        with self._auth("LECTURA"):
            editado = self.client.put(f"{self.base}/1", json={"monto": "100.00"}, headers=self._headers())
            eliminado = self.client.delete(f"{self.base}/1", headers=self._headers())
        self.assertEqual(editado.status_code, 403)
        self.assertEqual(eliminado.status_code, 403)


if __name__ == "__main__":
    unittest.main()
