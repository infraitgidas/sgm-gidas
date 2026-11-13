import unittest
from types import SimpleNamespace
from unittest.mock import patch

from extension import db
from tests import test_moneda_equipamiento_transferencia as fixtures
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.transferencia.models.transferencia_socio import TransferenciaSocioProductiva
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService as Transferencias
from modules.shared.exceptions import ValidationError


class MontosCeroTest(unittest.TestCase):
    setUp = fixtures.MonedaDomainTest.setUp
    tearDown = fixtures.MonedaDomainTest.tearDown
    _payload = fixtures.MonedaDomainTest._payload
    equipo = fixtures.MonedaDomainTest.equipo
    transferencia = fixtures.MonedaDomainTest.transferencia

    def test_cero_persiste_se_lista_y_se_audita_sin_perder_moneda(self):
        for create, service, field in [(self.equipo, EquipamientoService, "monto_invertido"), (self.transferencia, Transferencias, "monto")]:
            for moneda in ("ARS", "USD"):
                with self.subTest(field=field, moneda=moneda):
                    created = create(**{field: 0, "moneda": moneda})
                    self.assertEqual(created[field], 0)
                    service.update(created["id"], {field: 150.25}, 1)
                    updated = service.update(created["id"], {field: 0}, 1)
                    self.assertEqual((updated[field], updated["moneda"]), (0, moneda))
                    self.assertEqual(service.get_by_id(created["id"])[field], 0)
                    self.assertTrue(any(item["id"] == created["id"] and item[field] == 0 for item in service.get_all()))
                    self.assertTrue(any(item["campo"] == field and item["valor_nuevo"] == 0 for item in service.get_historial(created["id"])))

    def test_negativos_vacios_booleanos_y_no_finitos_se_rechazan(self):
        for service in (EquipamientoService, Transferencias):
            for value in (-1, "-0.01", "", None, True, False, float("nan"), float("inf")):
                with self.subTest(service=service, value=value), self.assertRaises(ValidationError):
                    service._validar_monto(value)
            self.assertEqual(service._validar_monto("0"), 0)
            self.assertEqual(service._validar_monto(1.25), 1.25)

    def test_fotos_conservan_importe_cero_y_moneda(self):
        for create, service, model, field, path in [
            (self.equipo, EquipamientoService, Equipamiento, "monto_invertido", "modules.recursos.services.equipamiento_service"),
            (self.transferencia, Transferencias, TransferenciaSocioProductiva, "monto", "modules.transferencia.services.transferencia_service"),
        ]:
            record = db.session.get(model, create(**{field: 0, "moneda": "USD"})["id"])
            with patch(f"{path}.consultar_entidades_memoria", return_value=[record]), patch(f"{path}.estuvo_activo_en_periodo_memoria", return_value=True):
                with db.session.no_autoflush:
                    foto = service.snapshot_para_memoria_version(SimpleNamespace(id=1), 1)[0]
                    self.assertEqual((getattr(foto, field), foto.moneda), (0, "USD"))
                db.session.rollback()
