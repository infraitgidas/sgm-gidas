import unittest
from datetime import date, timedelta
from unittest.mock import patch

import modules.models_registry  # noqa: F401
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.services.equipamiento_service import EquipamientoService


class EquipamientoServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.commit_patcher = patch("modules.recursos.services.equipamiento_service.db.session.commit")
        self.rollback_patcher = patch("modules.recursos.services.equipamiento_service.db.session.rollback")
        self.get_activo_patcher = patch(
            "modules.recursos.services.equipamiento_service.EquipamientoService._get_activo_or_404"
        )
        self.validar_grupo_patcher = patch(
            "modules.recursos.services.equipamiento_service.EquipamientoService._validar_grupo"
        )
        self.registrar_cambios_patcher = patch(
            "modules.recursos.services.equipamiento_service.AuditoriaService.registrar_cambios"
        )
        self.tiene_movimiento_patcher = patch(
            "modules.recursos.services.equipamiento_service.EquipamientoService._tiene_movimiento",
            return_value=False,
        )

        self.mock_commit = self.commit_patcher.start()
        self.mock_rollback = self.rollback_patcher.start()
        self.mock_get_activo = self.get_activo_patcher.start()
        self.mock_validar_grupo = self.validar_grupo_patcher.start()
        self.mock_registrar_cambios = self.registrar_cambios_patcher.start()
        self.mock_tiene_movimiento = self.tiene_movimiento_patcher.start()

        self.addCleanup(self.commit_patcher.stop)
        self.addCleanup(self.rollback_patcher.stop)
        self.addCleanup(self.get_activo_patcher.stop)
        self.addCleanup(self.validar_grupo_patcher.stop)
        self.addCleanup(self.registrar_cambios_patcher.stop)
        self.addCleanup(self.tiene_movimiento_patcher.stop)

    def _make_equipamiento(self):
        equipamiento = Equipamiento(
            id=1,
            denominacion="Microscopio",
            descripcion_breve="Equipo inicial",
            fecha_incorporacion=date(2024, 1, 10),
            monto_invertido=1500.0,
            grupo_utn_id=2,
            created_by=1
        )
        equipamiento.deleted_at = None
        equipamiento.updated_at = None
        equipamiento.updated_by = None
        return equipamiento

    def test_update_registra_auditoria_cuando_hay_cambios(self):
        equipamiento = self._make_equipamiento()
        self.mock_get_activo.return_value = equipamiento
        self.mock_validar_grupo.return_value = 3

        resultado = EquipamientoService.update(
            equipamiento_id=1,
            data={
                "denominacion": "Microscopio electronico",
                "monto_invertido": 2000,
                "grupo_utn_id": 3
            },
            user_id=99
        )

        self.assertEqual(equipamiento.denominacion, "Microscopio electronico")
        self.assertEqual(equipamiento.monto_invertido, 2000.0)
        self.assertEqual(equipamiento.grupo_utn_id, 3)
        self.assertEqual(equipamiento.updated_by, 99)
        self.assertIsNotNone(equipamiento.updated_at)
        self.assertEqual(resultado["updated_by"], 99)
        self.mock_registrar_cambios.assert_called_once()
        self.mock_commit.assert_called_once()

    def test_update_no_registra_auditoria_si_no_hay_cambios_reales(self):
        equipamiento = self._make_equipamiento()
        self.mock_get_activo.return_value = equipamiento
        self.mock_validar_grupo.return_value = 2

        EquipamientoService.update(
            equipamiento_id=1,
            data={
                "denominacion": "Microscopio",
                "grupo_utn_id": 2
            },
            user_id=50
        )

        self.assertIsNone(equipamiento.updated_at)
        self.assertIsNone(equipamiento.updated_by)
        self.mock_registrar_cambios.assert_not_called()
        self.mock_commit.assert_called_once()

    def test_no_cambia_grupo_si_el_equipo_esta_vinculado_a_un_movimiento(self):
        equipamiento = self._make_equipamiento()
        self.mock_get_activo.return_value = equipamiento
        self.mock_validar_grupo.return_value = 3
        self.mock_tiene_movimiento.return_value = True

        with self.assertRaisesRegex(ValueError, "vinculado a un movimiento"):
            EquipamientoService.update(1, {"grupo_utn_id": 3}, 99)
        self.assertEqual(equipamiento.grupo_utn_id, 2)
        self.mock_commit.assert_not_called()

    def test_delete_aplica_baja_logica_y_auditoria(self):
        equipamiento = self._make_equipamiento()
        self.mock_get_activo.return_value = equipamiento

        resultado = EquipamientoService.delete(
            equipamiento_id=1,
            user_id=99,
        )

        self.assertFalse(equipamiento.activo)
        self.assertIsNotNone(equipamiento.deleted_at)
        self.assertEqual(equipamiento.deleted_by, 99)
        self.assertEqual(resultado["message"], "Equipamiento eliminado correctamente")
        self.mock_commit.assert_called_once()

    def test_validar_fecha_acepta_limite_inferior(self):
        self.assertEqual(
            EquipamientoService._validar_fecha("2010-01-01"),
            date(2010, 1, 1),
        )

    def test_validar_fecha_rechaza_fecha_anterior_a_2010(self):
        with self.assertRaisesRegex(ValueError, "posterior al 01/01/2010"):
            EquipamientoService._validar_fecha("1900-01-01")

    def test_validar_fecha_acepta_fecha_actual(self):
        hoy = date.today()
        self.assertEqual(
            EquipamientoService._validar_fecha(hoy.isoformat()),
            hoy,
        )

    def test_validar_fecha_rechaza_fecha_futura(self):
        manana = date.today() + timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "no puede ser futura"):
            EquipamientoService._validar_fecha(manana.isoformat())

    def test_update_rechaza_fecha_anterior_a_2010_sin_persistir(self):
        self.mock_get_activo.return_value = self._make_equipamiento()

        with self.assertRaisesRegex(ValueError, "posterior al 01/01/2010"):
            EquipamientoService.update(
                equipamiento_id=1,
                data={"fecha_incorporacion": "1900-01-01"},
                user_id=99,
            )

        self.mock_commit.assert_not_called()
        self.mock_registrar_cambios.assert_not_called()

    def test_create_rechaza_fecha_anterior_a_2010_sin_persistir(self):
        with self.assertRaisesRegex(ValueError, "posterior al 01/01/2010"):
            EquipamientoService.create(
                data={
                    "denominacion": "Microscopio",
                    "descripcion_breve": "Equipo de laboratorio",
                    "fecha_incorporacion": "1900-01-01",
                    "monto_invertido": 1500,
                    "grupo_utn_id": 2,
                },
                user_id=99,
            )

        self.mock_commit.assert_not_called()
        self.mock_validar_grupo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
