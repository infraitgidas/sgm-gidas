import importlib.util
import unittest
from datetime import date, datetime, timedelta
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
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService as Service
from tests import test_trabajo_autores as fixtures


class FechaPresentacionTest(unittest.TestCase):
    setUp = fixtures.TrabajoAutoresTest.setUp
    tearDown = fixtures.TrabajoAutoresTest.tearDown
    payload = fixtures.TrabajoAutoresTest.payload

    def test_api_canonica_alias_conflicto_validacion_y_auditoria(self):
        payload = self.payload("reuniones")
        response = self.client.post("/reuniones", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.get_json())
        trabajo = response.get_json()
        self.assertEqual(trabajo["fecha_presentacion"], "2026-03-20")
        self.assertNotIn("fecha_inicio", trabajo)
        ruta = f"/reuniones/{trabajo['id']}"
        response = self.client.put(ruta, json={"fecha_inicio": "2026-03-21"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["fecha_presentacion"], "2026-03-21")
        response = self.client.put(ruta, json={"fecha_inicio": "2026-03-21", "fecha_presentacion": "2026-03-22"}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(ruta, headers=self.headers).get_json()["fecha_presentacion"], "2026-03-21")
        for fecha in ("2009-12-31", "2026-02-30"):
            self.assertEqual(self.client.put(ruta, json={"fecha_presentacion": fecha}, headers=self.headers).status_code, 400)
        historial = self.client.get(ruta + "/historial", headers=self.headers).get_json()
        self.assertEqual([i["campo"] for i in historial].count("fecha_presentacion"), 1)
        payload["titulo_trabajo"] = "Solicitud de consumidor anterior"
        payload["fecha_inicio"] = payload.pop("fecha_presentacion")
        self.assertEqual(self.client.post("/reuniones", json=payload, headers=self.headers).status_code, 201)

    def test_alta_y_edicion_aceptan_presentaciones_futuras(self):
        fecha_futura = (date.today() + timedelta(days=365)).isoformat()
        payload = {
            **self.payload("reuniones"),
            "titulo_trabajo": "Presentacion programada",
            "fecha_presentacion": fecha_futura,
        }

        response = self.client.post("/reuniones", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()["fecha_presentacion"], fecha_futura)

        nueva_fecha = (date.today() + timedelta(days=730)).isoformat()
        ruta = f"/reuniones/{response.get_json()['id']}"
        response = self.client.put(
            ruta,
            json={"fecha_presentacion": nueva_fecha},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["fecha_presentacion"], nueva_fecha)

    def test_limites_anuales_orden_y_excel_de_snapshot(self):
        ids = []
        for fecha in ("2025-12-31", "2026-01-01"):
            payload = {**self.payload("reuniones"), "titulo_trabajo": f"Ponencia del {fecha}", "fecha_presentacion": fecha}
            response = self.client.post("/reuniones", json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 201)
            ids.append(response.get_json()["id"])
        self.assertEqual([t["id"] for t in Service.get_all({"orden": "asc"})], ids)
        self.assertEqual([t["id"] for t in Service.get_all({"orden": "desc"})], ids[::-1])
        for anio, esperado in zip((2025, 2026), ids):
            memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(anio, 1, 1), periodo_fin=date(anio, 12, 31), created_by=7)
            db.session.add(memoria)
            db.session.flush()
            version = MemoriaVersion(memoria_id=memoria.id, numero_version=1, fecha_apertura=datetime(anio, 1, 1), estado=EstadoMemoria.CERRADA, created_by=7)
            db.session.add(version)
            db.session.flush()
            version.contexto_institucional = snapshot_contexto_institucional(version)
            snapshots = Service.snapshot_para_memoria_version(version, 7)
            db.session.commit()
            self.assertEqual([s.trabajo_reunion_id for s in snapshots], [esperado])
            self.assertEqual(snapshots[0].fecha_presentacion.year, anio)
            self.assertNotIn("fecha_inicio", snapshots[0].serialize())
            fuentes = {clave: [] for clave in ("investigadores", "becarios", "personal", "proyectos", "participaciones", "visitas", "articulos", "documentacion", "registros", "distinciones", "transferencias", "actividades", "erogaciones", "equipamiento", "becas", "planificaciones", "trabajos_revista")}
            fuentes.update(memoria=memoria, version=version, trabajos_reunion=[s.serialize() for s in snapshots])
            with patch.object(ExportService, "_build_memoria_snapshot_sources", return_value=fuentes):
                archivo = ExportService.generar_excel_memoria(memoria.id, version.id)
            libro = load_workbook(BytesIO(archivo.getvalue()))
            valores = [celda.value for hoja in libro for fila in hoja for celda in fila if celda.value is not None]
            self.assertIn("Fecha inicio", valores)  # Encabezado institucional fijo
            self.assertIn(snapshots[0].fecha_presentacion.strftime("%d/%m/%Y"), valores)


class MigracionFechaTest(unittest.TestCase):
    def test_upgrade_downgrade_preservan_trabajos_y_snapshots(self):
        ruta = Path(__file__).resolve().parents[1] / "migrations/versions/c13d7e9a2b40_fecha_presentacion_trabajos_reunion.py"
        spec = importlib.util.spec_from_file_location("iss13_migration", ruta)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            for tabla in migration.TABLAS:
                conn.exec_driver_sql(f"CREATE TABLE {tabla} (id INTEGER PRIMARY KEY, fecha_inicio DATE NOT NULL)")
                conn.exec_driver_sql(f"INSERT INTO {tabla} VALUES (1, '2025-12-31'), (2, '2026-01-01')")
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                for tabla in migration.TABLAS:
                    self.assertEqual(conn.exec_driver_sql(f"SELECT fecha_presentacion FROM {tabla} ORDER BY id").scalars().all(), ["2025-12-31", "2026-01-01"])
                migration.downgrade()
                for tabla in migration.TABLAS:
                    self.assertEqual(conn.exec_driver_sql(f"SELECT fecha_inicio FROM {tabla} ORDER BY id").scalars().all(), ["2025-12-31", "2026-01-01"])
