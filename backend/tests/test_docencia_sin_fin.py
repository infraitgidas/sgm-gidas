import importlib.util
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.models.personal import Investigador
from modules.produccion.models.actividad_docencia import ActividadDocencia, GradoAcademico, RolActividad
from modules.produccion.routes.actividad_docencia_rutas import actividad_docencia_bp
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService as Docencia
from modules.shared.exceptions import ValidationError


class DocenciaSinFinTest(unittest.TestCase):
    tearDown = fixtures.PersonalAltaPTAATest.tearDown

    def setUp(self):
        fixtures.PersonalAltaPTAATest.setUp(self)
        self.app.register_blueprint(actividad_docencia_bp, url_prefix="/api/v1/actividades-docencia")
        db.session.add_all([GradoAcademico(id=1, nombre="Doctor"), RolActividad(id=1, nombre="Titular"),
            Investigador(id=1, nombre_apellido="Persona Docente", grupo_utn_id=1, horas_semanales=20)])
        db.session.commit()
        self.payload = dict(curso="Curso de prueba", institucion="UTN", fecha_inicio="2026-01-01",
                            grado_academico_id=1, rol_actividad_id=1, investigador_id=1)
        self.headers = {"Authorization": "Bearer test"}

    def test_alta_consulta_edicion_cierre_y_reapertura_auditada(self):
        response = self.client.post("/api/v1/actividades-docencia/", json=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        record_id = response.get_json()["id"]
        endpoint = f"/api/v1/actividades-docencia/{record_id}"
        self.assertIsNone(response.get_json()["fecha_fin"])
        self.assertIsNone(self.client.get(endpoint, headers=self.headers).get_json()["fecha_fin"])
        self.assertIsNone(self.client.get("/api/v1/actividades-docencia", headers=self.headers).get_json()[0]["fecha_fin"])
        for payload in ({"curso": "Curso actualizado"}, {"fecha_fin": "2026-12-01"}, {"fecha_fin": None}):
            updated = self.client.put(endpoint, json=payload, headers=self.headers)
            self.assertEqual(updated.status_code, 200)
        history = self.client.get(f"{endpoint}/historial", headers=self.headers).get_json()
        end_changes = [item for item in history if item.get("campo") == "fecha_fin"]
        self.assertEqual(len(end_changes), 2)
        self.assertIsNone(end_changes[0]["valor_nuevo"])
        self.assertEqual(end_changes[0]["valor_anterior"], "2026-12-01")

    def test_fin_invalido_se_rechaza_y_null_no_afecta_inicio_obligatorio(self):
        for fin in ("2025-12-31", "2026-02-30", "invalida"):
            with self.subTest(fin=fin), self.assertRaises(ValidationError):
                Docencia.create({**self.payload, "fecha_fin": fin}, 1)
            db.session.rollback()
        for inicio in (None, "", "9999-01-01"):
            with self.subTest(inicio=inicio), self.assertRaises(ValidationError):
                Docencia.create({**self.payload, "fecha_inicio": inicio, "fecha_fin": None}, 1)
            db.session.rollback()

    def test_foto_de_memoria_conserva_fin_abierto_tras_cerrar_actividad(self):
        created = Docencia.create({**self.payload, "fecha_fin": None}, 1)
        actividad = db.session.get(ActividadDocencia, created["id"])
        with patch("modules.produccion.services.actividad_docencia_service.consultar_entidades_memoria", return_value=[actividad]), patch(
            "modules.produccion.services.actividad_docencia_service.estuvo_activo_en_periodo_memoria", return_value=True
        ):
            foto = Docencia.snapshot_para_memoria_version(SimpleNamespace(id=1), 1)[0]
            db.session.commit()
        Docencia.update(actividad.id, {"fecha_fin": "2026-12-01"}, 1)
        self.assertIsNone(foto.fecha_fin)
        self.assertEqual(actividad.fecha_fin, date(2026, 12, 1))


class DocenciaSinFinMigrationTest(unittest.TestCase):
    def test_upgrade_preserva_fechas_y_downgrade_no_inventa_valores(self):
        path = Path(__file__).parents[1] / "migrations/versions/c3e5a7b9d1f2_docencia_fecha_fin_opcional.py"
        spec = importlib.util.spec_from_file_location("docencia_fin_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            for table in migration.TABLAS:
                connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, fecha_fin DATE NOT NULL)")
                connection.exec_driver_sql(f"INSERT INTO {table} VALUES (1, '2026-12-01')")
            with patch.object(migration, "op", Operations(MigrationContext.configure(connection))):
                migration.upgrade()
                for table in migration.TABLAS:
                    connection.exec_driver_sql(f"INSERT INTO {table} VALUES (2, NULL)")
                    self.assertEqual(connection.exec_driver_sql(f"SELECT fecha_fin FROM {table} WHERE id=1").scalar_one(), "2026-12-01")
                with self.assertRaises(RuntimeError):
                    migration.downgrade()
                for table in migration.TABLAS:
                    connection.exec_driver_sql(f"UPDATE {table} SET fecha_fin='2026-12-01' WHERE fecha_fin IS NULL")
                migration.downgrade()
                self.assertTrue(all(not col["nullable"] for table in migration.TABLAS for col in sa.inspect(connection).get_columns(table) if col["name"] == "fecha_fin"))
