import unittest
import importlib
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from modules.shared.exceptions import ConflictError, ValidationError


class ProyectoProrrogaTestCase(unittest.TestCase):
    def test_migracion_conserva_fechas_existentes(self):
        migration = importlib.import_module("migrations.versions.e77a1b2c3d4e_project_extensions")
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(sa.text("CREATE TABLE usuario (id INTEGER PRIMARY KEY)"))
            connection.execute(sa.text("CREATE TABLE proyecto_investigacion (id INTEGER PRIMARY KEY, fecha_fin DATE)"))
            connection.execute(sa.text("INSERT INTO proyecto_investigacion VALUES (1, '2025-06-30')"))
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()
            result = connection.execute(sa.text(
                "SELECT fecha_fin, fecha_fin_original, fecha_fin_prorrogada FROM proyecto_investigacion WHERE id = 1"
            )).one()
            self.assertEqual(result, ("2025-06-30", "2025-06-30", None))

    def test_duracion_inclusiva_entre_12_y_36_meses(self):
        inicio = date(2024, 1, 1)
        for fin in (date(2024, 12, 31), date(2026, 12, 31)):
            ProyectoInvestigacionService._validar_duracion(inicio, fin)
        for fin in (None, date(2024, 12, 30), date(2027, 1, 1)):
            with self.subTest(fin=fin), self.assertRaises(ValidationError) as error:
                ProyectoInvestigacionService._validar_duracion(inicio, fin)
            self.assertIn("fecha_fin", error.exception.details["fields"])
        ProyectoInvestigacionService._validar_duracion(date(2024, 2, 29), date(2025, 2, 28))

    def test_prorroga_conserva_original_y_registra_decision(self):
        proyecto = SimpleNamespace(
            id=5, fecha_inicio=date(2024, 1, 1), fecha_fin=date(2026, 12, 31),
            fecha_fin_original=None, fecha_fin_prorrogada=None,
            mark_updated=lambda user_id: None,
            serialize=lambda: {"fecha_fin": proyecto.fecha_fin.isoformat()},
        )
        with patch.object(ProyectoInvestigacionService, "_get_proyecto_activo_or_404", return_value=proyecto), \
             patch("modules.proyectos.services.proyecto_investigacion_service.AuditoriaService.registrar_cambios") as audit, \
             patch("modules.proyectos.services.proyecto_investigacion_service.db.session.commit"):
            result = ProyectoInvestigacionService.prorrogar_proyecto(5, {"motivo": "Resultados pendientes"}, 7)
        self.assertEqual(result["fecha_fin"], "2027-12-31")
        self.assertEqual(proyecto.fecha_fin_original, date(2026, 12, 31))
        self.assertEqual(proyecto.prorroga_by, 7)
        self.assertEqual(audit.call_args.args[2]["prorroga"]["valor_nuevo"]["motivo"], "Resultados pendientes")
        with patch.object(ProyectoInvestigacionService, "_get_proyecto_activo_or_404", return_value=proyecto), \
             self.assertRaises(ConflictError):
            ProyectoInvestigacionService.prorrogar_proyecto(5, {"motivo": "Segunda extensión"}, 7)

    def test_prorroga_exige_motivo(self):
        proyecto = SimpleNamespace(fecha_fin_prorrogada=None)
        with patch.object(ProyectoInvestigacionService, "_get_proyecto_activo_or_404", return_value=proyecto):
            for payload in ({}, {"motivo": "   "}, {"motivo": "breve"}):
                with self.subTest(payload=payload), self.assertRaises(ValidationError) as error:
                    ProyectoInvestigacionService.prorrogar_proyecto(5, payload, 7)
                self.assertIn("motivo", error.exception.details["fields"])
