import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from modules.produccion.models.distinciones import DistincionRecibida
from modules.produccion.services.distincion_service import DistincionRecibidaService as Service
from modules.shared.exceptions import ValidationError

MODULE = "modules.produccion.services.distincion_service."


class DistincionProyectoOpcionalTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch(MODULE + "db.session.commit"))
        self.add = self.enterContext(patch(MODULE + "db.session.add"))
        self.enterContext(patch.object(Service, "_validar_no_duplicado"))

    def test_create_without_project_omitted_or_null(self):
        for extra in ({}, {"proyecto_investigacion_id": None}):
            with self.subTest(extra=extra):
                result = Service.create({"fecha": "2025-01-01", "descripcion": "Trayectoria", **extra}, 1)
                self.assertIsNone(result["proyecto"])
                self.assertIsNone(self.add.call_args.args[0].proyecto_investigacion_id)

    def test_project_validation_keeps_existing_rules(self):
        for value in (0, -1, True, "1", ""):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Service._validar_proyecto(value)
        with patch(MODULE + "db.session.get", return_value=SimpleNamespace(id=3, deleted_at=None)):
            self.assertEqual(Service._validar_proyecto(3), 3)
        with patch(MODULE + "db.session.get", return_value=None), self.assertRaises(ValidationError):
            Service._validar_proyecto(999)

    def test_unlink_relink_and_omitted_update_are_audited(self):
        dist = DistincionRecibida(id=2, fecha=date(2025, 1, 1), descripcion="Trayectoria", proyecto_investigacion_id=3)
        with patch.object(Service, "_get_activa_or_404", return_value=dist), patch(MODULE + "AuditoriaService.registrar_cambios") as audit:
            Service.update(2, {"descripcion": "Trayectoria nacional"}, 1)
            self.assertEqual(dist.proyecto_investigacion_id, 3)
            Service.update(2, {"proyecto_investigacion_id": None}, 1)
            self.assertIsNone(dist.proyecto_investigacion_id)
            self.assertIn("proyecto_investigacion_id", audit.call_args.kwargs["cambios"])
            with patch(MODULE + "db.session.get", return_value=SimpleNamespace(id=3, deleted_at=None)):
                Service.update(2, {"proyecto_investigacion_id": 3}, 1)
            self.assertEqual(dist.proyecto_investigacion_id, 3)
