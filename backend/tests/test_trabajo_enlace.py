import importlib.util
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from openpyxl import load_workbook

from extension import db
from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.memorias.services.memoria_contexto_service import snapshot_contexto_institucional
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService
from tests import test_trabajo_autores as fixtures


class EnlaceTrabajoTest(unittest.TestCase):
    setUp = fixtures.TrabajoAutoresTest.setUp
    tearDown = fixtures.TrabajoAutoresTest.tearDown
    payload = fixtures.TrabajoAutoresTest.payload

    def test_api_opcional_validacion_edicion_y_auditoria(self):
        for tipo in ("reuniones", "revistas"):
            response = self.client.post(f"/{tipo}", json=self.payload(tipo), headers=self.headers)
            self.assertEqual(response.status_code, 201, response.get_json())
            ruta = f"/{tipo}/{response.get_json()['id']}"
            self.assertIsNone(response.get_json()["enlace"])
            validos = (None, "", "  ", "http://example.org", " https://doi.org/10.1234/test ", "https://example.org/" + "a" * 2028)
            for enlace in validos:
                response = self.client.put(ruta, json={"enlace": enlace}, headers=self.headers)
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual(response.get_json()["enlace"], enlace.strip() or None if enlace else None)
            invalidos = (123, {}, "javascript:alert(1)", "ftp://example.org", "//example.org", "https://", "https://user:pass@example.org", "https://@example.org", "https://example.org:99999", "https://example.org/a b", "https://%", "https://<invalid>", "https://invalid_host/", "https://example.org/" + "a" * 2029)
            anterior = self.client.get(ruta, headers=self.headers).get_json()
            for enlace in invalidos:
                response = self.client.put(ruta, json={"enlace": enlace, "titulo_trabajo": "No debe persistirse"}, headers=self.headers)
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertIn("enlace", response.get_json()["error"]["details"]["fields"])
                self.assertEqual(self.client.get(ruta, headers=self.headers).get_json(), anterior)
                response = self.client.post(f"/{tipo}", json={**self.payload(tipo), "titulo_trabajo": "Alta inválida", "enlace": enlace}, headers=self.headers)
                self.assertEqual(response.status_code, 400)
            eventos = self.client.get(ruta + "/historial", headers=self.headers).get_json()
            self.client.put(ruta, json={"enlace": anterior["enlace"]}, headers=self.headers)
            self.assertEqual(self.client.get(ruta + "/historial", headers=self.headers).get_json(), eventos)
            self.client.put(ruta, json={"enlace": None}, headers=self.headers)
            self.assertIsNone(self.client.get(ruta, headers=self.headers).get_json()["enlace"])
            self.assertTrue(any(e["campo"] == "enlace" for e in eventos))

    def test_snapshot_y_excel_conservan_enlace_original(self):
        memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31), created_by=7)
        db.session.add(memoria)
        db.session.flush()
        version = MemoriaVersion(memoria_id=memoria.id, numero_version=1, fecha_apertura=datetime(2026, 1, 1), estado=EstadoMemoria.CERRADA, created_by=7)
        db.session.add(version)
        db.session.flush()
        version.contexto_institucional = snapshot_contexto_institucional(version)
        fuentes = {clave: [] for clave in ("investigadores", "becarios", "personal", "proyectos", "participaciones", "visitas", "articulos", "documentacion", "registros", "distinciones", "transferencias", "actividades", "erogaciones", "equipamiento", "becas", "planificaciones")}
        for tipo, service, clave in (("reuniones", TrabajoReunionCientificaService, "trabajos_reunion"), ("revistas", TrabajosRevistasReferatoService, "trabajos_revista")):
            enlace = f"https://example.org/{tipo}"
            trabajo = service.create({**self.payload(tipo), "enlace": enlace}, 7)
            snapshots = service.snapshot_para_memoria_version(version, 7)
            db.session.commit()
            service.update(trabajo["id"], {"enlace": None}, 7)
            self.assertEqual(snapshots[0].serialize()["enlace"], enlace)
            fuentes[clave] = [s.serialize() for s in snapshots]
        fuentes.update(memoria=memoria, version=version)
        with patch.object(ExportService, "_build_memoria_snapshot_sources", return_value=fuentes):
            archivo = ExportService.generar_excel_memoria(memoria.id, version.id)
        libro = load_workbook(BytesIO(archivo.getvalue()))
        texto = "\n".join(str(c.value) for h in libro for f in h for c in f if c.value)
        for tipo in ("reuniones", "revistas"):
            self.assertIn(f"Enlace: https://example.org/{tipo}", texto)


class MigracionEnlaceTest(unittest.TestCase):
    def test_upgrade_downgrade_con_registros_existentes(self):
        ruta = Path(__file__).resolve().parents[1] / "migrations/versions/d14e8f0a3c51_enlace_opcional_trabajos.py"
        spec = importlib.util.spec_from_file_location("iss14_migration", ruta)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            for tabla in migration.TABLAS:
                conn.exec_driver_sql(f"CREATE TABLE {tabla} (id INTEGER PRIMARY KEY)")
                conn.exec_driver_sql(f"INSERT INTO {tabla} VALUES (1)")
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                for tabla in migration.TABLAS:
                    self.assertIsNone(conn.exec_driver_sql(f"SELECT enlace FROM {tabla}").scalar())
                migration.downgrade()
                for tabla in migration.TABLAS:
                    self.assertEqual(conn.exec_driver_sql(f"SELECT id FROM {tabla}").scalar(), 1)
                    self.assertNotIn("enlace", [c["name"] for c in sa.inspect(conn).get_columns(tabla)])
