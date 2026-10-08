import unittest
import importlib
from datetime import date
from unittest.mock import patch

from flask import Flask, g
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.informes.models.informe import Informe
from modules.informes.routes.informe_rutas import informe_bp
from modules.informes.services.informe_service import InformeService
from modules.memorias.models.memorias import Memoria
from modules.memorias.services.memoria_service import MemoriaService
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, TipoProyecto
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError


class InformesTest(unittest.TestCase):
    def test_migracion_crea_relaciones_y_revierte(self):
        migration = importlib.import_module("migrations.versions.a85f1e2d3c4b_informes_por_periodo")
        engine = sa.create_engine("sqlite://")
        with engine.begin() as connection:
            for table in ("usuario", "memoria", "grupo_utn", "investigador", "proyecto_investigacion"):
                connection.execute(sa.text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(sa.text("CREATE TABLE auditoria_campo (id INTEGER PRIMARY KEY, entidad VARCHAR(100))"))
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()
                names = set(sa.inspect(connection).get_table_names())
                self.assertTrue({"informe", "informe_investigador", "informe_proyecto"}.issubset(names))
                self.assertTrue({"memoria_id", "grupo_utn_id", "fecha_realizacion", "uct_snapshot"}.issubset({item["name"] for item in sa.inspect(connection).get_columns("informe")}))
                migration.downgrade()
                self.assertNotIn("informe", sa.inspect(connection).get_table_names())

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(informe_bp, url_prefix="/api/v1/informes")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        db.session.add_all([
            GrupoInvestigacionUtn(id=i, nombre_sigla_grupo=f"UCT {i}", mail=f"uct{i}@test.invalid", nombre_unidad_academica="Regional", objetivo_desarrollo="Objetivos")
            for i in (1, 2)
        ])
        db.session.add(TipoProyecto(id=1, nombre="PID"))
        db.session.flush()
        db.session.add_all([
            Memoria(id=1, grupo_utn_id=1, periodo_inicio=date(2024, 1, 1), periodo_fin=date(2024, 12, 31)),
            Memoria(id=2, grupo_utn_id=1, periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31)),
            Memoria(id=3, grupo_utn_id=2, periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31)),
            Memoria(id=4, grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31)),
            ProyectoInvestigacion(id=1, codigo_proyecto="PID1", nombre_proyecto="Proyecto uno", descripcion_proyecto="Descripción", fecha_inicio=date(2024, 1, 1), fecha_fin=date(2025, 12, 31), tipo_proyecto_id=1, grupo_utn_id=1),
            ProyectoInvestigacion(id=2, codigo_proyecto="PID2", nombre_proyecto="Proyecto ajeno", descripcion_proyecto="Descripción", fecha_inicio=date(2024, 1, 1), fecha_fin=date(2025, 12, 31), tipo_proyecto_id=1, grupo_utn_id=2),
            ProyectoInvestigacion(id=3, codigo_proyecto="PID3", nombre_proyecto="Proyecto tres", descripcion_proyecto="Descripción", fecha_inicio=date(2024, 1, 1), fecha_fin=date(2026, 12, 31), tipo_proyecto_id=1, grupo_utn_id=1),
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def payload(self, memoria_id, project_id):
        return {"memoria_id": memoria_id, "titulo": "Informe anual", "fecha_realizacion": "2025-12-31", "resumen": "Resumen", "actividades": "Actividades", "resultados": "Resultados", "observaciones": "Observaciones", "vinculos_ids": [project_id]}

    def test_periodos_distintos_y_snapshot_no_cambia_con_proyecto(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            first = InformeService.create("pid", self.payload(1, 1), 1)
            second = InformeService.create("pid", self.payload(2, 1), 1)
            self.assertNotEqual(first["id"], second["id"])
            grupo = db.session.get(GrupoInvestigacionUtn, 1)
            grupo.nombre_sigla_grupo = "Otro nombre"
            db.session.commit()
            self.assertEqual(InformeService.get("pid", first["id"])["uct_snapshot"]["nombre_sigla_grupo"], "UCT 1")
            proyecto = db.session.get(ProyectoInvestigacion, 1)
            proyecto.nombre_proyecto = "Nuevo nombre"
            db.session.commit()
            self.assertEqual(InformeService.get("pid", first["id"])["proyectos"][0]["snapshot"]["nombre_proyecto"], "Proyecto uno")
            InformeService.update("pid", first["id"], {"titulo": "Informe editado", "vinculos_ids": [1]}, 1)
            self.assertEqual(InformeService.get("pid", first["id"])["proyectos"][0]["snapshot"]["nombre_proyecto"], "Proyecto uno")
            self.assertEqual(InformeService.get("pid", first["id"])["proyectos"][0]["snapshot"]["_version"], 1)
            page, total = InformeService.list("pid", page=1, per_page=1)
            self.assertEqual(total, 2)
            self.assertNotIn("resumen", page[0])
            self.assertNotIn("uct_snapshot", page[0])

    def test_aislamiento_uct_y_cierre_exigen_informe_del_periodo(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            with self.assertRaises(ValidationError):
                InformeService.create("pid", self.payload(3, 1), 1)
            with self.assertRaises(ValidationError):
                InformeService.create("pid", self.payload(2, 2), 1)
            proyecto = db.session.get(ProyectoInvestigacion, 1)
            self.assertFalse(ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto))
            old = InformeService.create("pid", self.payload(1, 1), 1)
            self.assertFalse(ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto))
            g.current_grupo_utn_id = 2
            InformeService.create("pid", self.payload(3, 2), 1)
            g.current_grupo_utn_id = 1
            self.assertFalse(ProyectoInvestigacionService._serializar_lista([proyecto])[0]["cerrado"])
            self.assertIn(1, [item["id"] for item in ProyectoInvestigacionService.get_all({"activos": "true", "grupo_utn_id": 1})])
            current = InformeService.create("pid", self.payload(2, 1), 1)
            self.assertFalse(ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto))
            self.assertFalse(ProyectoInvestigacionService._serializar_lista([proyecto])[0]["cerrado"])
            self.assertIn(1, [item["id"] for item in ProyectoInvestigacionService.get_all({"activos": "true", "grupo_utn_id": 1})])
            self.assertNotIn(1, [item["id"] for item in ProyectoInvestigacionService.get_all({"activos": "false", "grupo_utn_id": 1})])
            ProyectoInvestigacionService.cerrar_proyecto(1, 1, "2025-12-31")
            self.assertTrue(ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto))
            self.assertNotIn(1, [item["id"] for item in ProyectoInvestigacionService.get_all({"activos": "true", "grupo_utn_id": 1})])
            self.assertIn(1, [item["id"] for item in ProyectoInvestigacionService.get_all({"activos": "false", "grupo_utn_id": 1})])
            self.assertEqual(InformeService.delete("pid", old["id"], 1)["message"], "Informe eliminado con éxito")
            with self.assertRaises(ConflictError):
                InformeService.delete("pid", current["id"], 1)
            with self.assertRaises(ConflictError):
                InformeService.update("pid", current["id"], {"vinculos_ids": [3]}, 1)
            self.assertEqual(len(InformeService.history("pid", current["id"])), 0)
            self.assertEqual(InformeService.get("pid", current["id"])["memoria_id"], 2)

    def test_rutas_solo_gestor(self):
        client = self.app.test_client()
        for role, expected in (("GESTOR", 200), ("ADMIN", 403), ("LECTURA", 403)):
            with self.subTest(role=role), patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "1", "rol": role}), patch.object(InformeService, "list", return_value=([], 0)):
                response = client.get("/api/v1/informes/pid", headers={"Authorization": "Bearer test"})
                self.assertEqual(response.status_code, expected)
        self.assertEqual(client.get("/api/v1/informes/pid").status_code, 401)

    def test_candidatos_paginados_respetan_periodo_y_uct(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            first, total = InformeService.candidates("pid", 1, page=1, per_page=1)
            second, _ = InformeService.candidates("pid", 1, page=2, per_page=1)
            self.assertEqual(total, 2)
            self.assertNotEqual(first[0]["id"], second[0]["id"])
            self.assertEqual({first[0]["id"], second[0]["id"]}, {1, 3})
            self.assertEqual(InformeService.candidates("pid", 1, search="PID3")[1], 1)
            with self.assertRaises(ValidationError):
                InformeService.candidates("pid", 3)

    def test_detalle_e_historial_no_exponen_otra_uct(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 2
            foreign = InformeService.create("pid", self.payload(3, 2), 1)
            g.current_grupo_utn_id = 1
            self.assertEqual(InformeService.list("pid")[1], 0)
            with self.assertRaises(NotFoundError):
                InformeService.get("pid", foreign["id"])
            with self.assertRaises(NotFoundError):
                InformeService.history("pid", foreign["id"])

    def test_cierre_manual_espera_informe_del_periodo_de_cierre(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            with self.assertRaises(ConflictError):
                ProyectoInvestigacionService.cerrar_proyecto(3, 1, date.today().isoformat())
            payload = self.payload(4, 3)
            payload["fecha_realizacion"] = date.today().isoformat()
            report = InformeService.create("pid", payload, 1)
            result = ProyectoInvestigacionService.cerrar_proyecto(3, 1, date.today().isoformat())
            self.assertEqual(result["message"], "Proyecto cerrado correctamente")
            self.assertTrue(ProyectoInvestigacionService._proyecto_esta_cerrado(db.session.get(ProyectoInvestigacion, 3)))
            self.assertEqual(report["memoria_id"], 4)

    def test_informe_de_periodo_anterior_habilita_cierre_solo_en_ese_periodo(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            InformeService.create("pid", self.payload(1, 3), 1)
            with self.assertRaises(ConflictError):
                ProyectoInvestigacionService.cerrar_proyecto(3, 1, date.today().isoformat())
            result = ProyectoInvestigacionService.cerrar_proyecto(3, 1, "2024-12-31")
            self.assertEqual(result["message"], "Proyecto cerrado correctamente")
            self.assertTrue(ProyectoInvestigacionService._proyecto_esta_cerrado(db.session.get(ProyectoInvestigacion, 3)))

    def test_informe_de_proyecto_abierto_no_cierra_ni_bloquea_su_baja(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            report = InformeService.create("pid", self.payload(2, 1), 1)
            proyecto = db.session.get(ProyectoInvestigacion, 1)
            self.assertFalse(proyecto.serialize()["cerrado"])
            self.assertFalse(ProyectoInvestigacionService._serializar_lista([proyecto])[0]["cerrado"])
            self.assertEqual(InformeService.delete("pid", report["id"], 1)["message"], "Informe eliminado con éxito")
            self.assertFalse(proyecto.serialize()["cerrado"])

    def test_memoria_con_informe_no_cambia_periodo_ni_se_elimina(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            InformeService.create("uct", {**self.payload(2, 1), "vinculos_ids": []}, 1)
            with self.assertRaises(ConflictError):
                MemoriaService.update(2, {"periodo_fin": "2025-11-30"}, 1)
            with self.assertRaises(ConflictError):
                MemoriaService.delete(2, 1)
            self.assertEqual(db.session.get(Memoria, 2).periodo_fin, date(2025, 12, 31))

    def test_edicion_registra_diferencias_y_relaciones_una_vez(self):
        with self.app.test_request_context():
            g.current_grupo_utn_id = 1
            informe = InformeService.create("pid", self.payload(1, 1), 1)
            edited = InformeService.update("pid", informe["id"], {"titulo": "Informe corregido", "vinculos_ids": [1, 3]}, 1)
            self.assertEqual(len(edited["proyectos"]), 2)
            history = InformeService.history("pid", informe["id"])
            self.assertEqual({item["campo"] for item in history}, {"titulo", "vinculos_ids"})
            InformeService.update("pid", informe["id"], {"titulo": "Informe corregido", "vinculos_ids": [1, 3]}, 1)
            self.assertEqual(len(InformeService.history("pid", informe["id"])), 2)
