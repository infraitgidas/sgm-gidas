import importlib.util
import unittest
from datetime import date, datetime
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from openpyxl import load_workbook

from extension import db
from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService as Reuniones
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService as Revistas
from tests import test_trabajo_autores as fixtures
from tests import test_memoria_excel_formato as formato


class ClasificacionTest(unittest.TestCase):
    setUp = fixtures.TrabajoAutoresTest.setUp
    tearDown = fixtures.TrabajoAutoresTest.tearDown
    payload = fixtures.TrabajoAutoresTest.payload

    def test_api_diferencias_null_false_validacion_y_permisos(self):
        for tipo in ("reuniones", "revistas"):
            with self.subTest(tipo=tipo):
                response = self.client.post(f"/{tipo}", json=self.payload(tipo), headers=self.headers)
                self.assertEqual(response.status_code, 201, response.get_json())
                self.assertIsNone(response.get_json()["referato"])
                ruta = f"/{tipo}/{response.get_json()['id']}"
                for invalido in ("false", "true", 0, 1, [], {}):
                    response = self.client.put(ruta, json={"referato": invalido}, headers=self.headers)
                    self.assertEqual(response.status_code, 400, response.get_json())
                    self.assertIn("referato", response.get_json()["error"]["details"]["fields"])
                for valor in (True, False, None):
                    for repeticion in range(2):
                        response = self.client.put(ruta, json={"referato": valor}, headers=self.headers)
                        self.assertEqual(response.status_code, 200, response.get_json())
                        self.assertIs(response.get_json()["referato"], valor)
                    # An unrelated update must preserve false as well as true/null.
                    response = self.client.put(ruta, json={"enlace": None}, headers=self.headers)
                    self.assertIs(response.get_json()["referato"], valor)
                history = self.client.get(ruta + "/historial", headers=self.headers).get_json()
                events = [h for h in history if h["campo"] == "referato"]
                self.assertEqual(len(events), 3)
                self.assertEqual(self.client.put(ruta, json={"referato": True}).status_code, 401)
                if tipo == "reuniones":
                    for valor in ([], {}, "local", False):
                        self.assertEqual(self.client.put(ruta, json={"alcance": valor}, headers=self.headers).status_code, 400)
                    for valor in ("nacional", "internacional", None):
                        response = self.client.put(ruta, json={"alcance": valor}, headers=self.headers)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.get_json()["alcance"], valor)

    def test_snapshots_inmutables_y_exportacion_de_grupo(self):
        reunion = Reuniones.create({**self.payload("reuniones"), "alcance": "nacional", "referato": True, "procedencia": "Córdoba"}, 7)
        revista = Revistas.create({**self.payload("revistas"), "referato": True}, 7)
        memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31), created_by=7)
        db.session.add(memoria)
        db.session.flush()
        version = MemoriaVersion(memoria_id=memoria.id, numero_version=1, fecha_apertura=datetime(2026, 1, 1), estado=EstadoMemoria.CERRADA, created_by=7)
        db.session.add(version)
        db.session.flush()
        reuniones = Reuniones.snapshot_para_memoria_version(version, 7)
        revistas = Revistas.snapshot_para_memoria_version(version, 7)
        db.session.commit()
        Reuniones.update(reunion["id"], {"referato": False, "alcance": "internacional"}, 7)
        Revistas.update(revista["id"], {"referato": False}, 7)
        self.assertIs(reuniones[0].serialize()["referato"], True)
        self.assertEqual(reuniones[0].serialize()["alcance"], "nacional")
        self.assertIs(revistas[0].serialize()["referato"], True)
        # Current group export uses current classification; no false publication in 8.1.
        output = ExportService.generar_excel_grupo(1)
        workbook = load_workbook(output)
        text = "\n".join(str(c.value) for s in workbook for row in s for c in row if c.value is not None)
        self.assertIn("7.1.- Reunión Científica Nacional con Referato", text)
        self.assertIn("7.2.- Reunión Científica Internacional", text)
        self.assertIn("Publicaciones sin clasificar para la memoria", text)


class ClasificacionExcelTest(unittest.TestCase):
    def test_tablas_y_geografia_preservan_formato_y_no_duplican(self):
        output = formato.MemoriaFormatoTest().render(trabajos_reunion=[
            {"nombre_reunion": "Reunión nacional", "titulo_trabajo": "Ponencia nacional", "alcance": "nacional", "referato": True, "procedencia": "Córdoba"},
            {"nombre_reunion": "Reunión internacional", "titulo_trabajo": "Ponencia internacional", "alcance": "internacional", "referato": False, "procedencia": "Uruguay"},
            {"titulo_trabajo": "Ponencia sin revisión", "alcance": "nacional", "referato": False},
            {"titulo_trabajo": "Ponencia histórica", "tipo_reunion_nombre": "Congreso"},
        ], trabajos_revista=[
            {"titulo_trabajo": "Revista revisada", "tipo_revista_nombre": "Nacional", "referato": True},
            {"titulo_trabajo": "Revista no revisada", "tipo_revista_nombre": "Internacional", "referato": False},
        ])
        sheet = output["Hoja1"]
        self.assertEqual(sheet["C211"].value, "Ciudad")
        self.assertEqual(sheet["C220"].value, "País")
        self.assertEqual(sheet["C212"].value, "Córdoba")
        self.assertEqual(sheet["C221"].value, "Uruguay")
        main = formato.MemoriaFormatoTest.text(sheet)
        detail = formato.MemoriaFormatoTest.text(output["Detalle académico"])
        for titulo in ("Ponencia nacional", "Ponencia internacional", "Revista revisada"):
            self.assertEqual(main.count(titulo), 1)
        for titulo in ("Ponencia sin revisión", "Ponencia histórica", "Revista no revisada"):
            self.assertNotIn(titulo, main)
            self.assertIn(titulo, detail)

    def test_migracion_reversible_conserva_registros_sin_inferencias(self):
        path = Path(__file__).parents[1] / "migrations/versions/e8c2a4f6b0d1_clasificacion_trabajos.py"
        spec = importlib.util.spec_from_file_location("clasificacion_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with sa.create_engine("sqlite://").begin() as conn:
            for tabla in migration.REUNIONES + migration.REVISTAS:
                conn.exec_driver_sql(f"CREATE TABLE {tabla} (id INTEGER PRIMARY KEY)")
                conn.exec_driver_sql(f"INSERT INTO {tabla} (id) VALUES (1)")
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
                for tabla in migration.REUNIONES + migration.REVISTAS:
                    self.assertIsNone(conn.exec_driver_sql(f"SELECT referato FROM {tabla}").scalar())
                for tabla in migration.REUNIONES:
                    self.assertIsNone(conn.exec_driver_sql(f"SELECT alcance FROM {tabla}").scalar())
                    with self.assertRaises(sa.exc.IntegrityError):
                        conn.exec_driver_sql(f"UPDATE {tabla} SET alcance = 'local'")
                migration.downgrade()
                for tabla in migration.REUNIONES + migration.REVISTAS:
                    self.assertEqual([c["name"] for c in sa.inspect(conn).get_columns(tabla)], ["id"])
                    self.assertEqual(conn.exec_driver_sql(f"SELECT id FROM {tabla}").scalar(), 1)
