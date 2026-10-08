import importlib.util
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from modules import models_registry  # noqa: F401
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.memorias.services.memoria_service import MemoriaService
from modules.proyectos.services.participacion_relevante_service import (
    ParticipacionRelevanteService,
)
from modules.shared.exceptions import ValidationError


class ParticipacionRelevanteMemoriaHistorialTestCase(unittest.TestCase):

    def test_evento_vacio_identifica_el_campo_sin_persistir(self):
        with patch("modules.proyectos.services.participacion_relevante_service.db.session.add") as add:
            with self.assertRaises(ValidationError) as caught:
                ParticipacionRelevanteService.create({"nombre_evento": ""}, 1)
            self.assertEqual(caught.exception.details["fields"], {
                "nombre_evento": "Ingrese nombre del evento."
            })
            add.assert_not_called()

    def test_fecha_fuera_del_rango_identifica_el_campo(self):
        with self.assertRaises(ValidationError) as caught:
            ParticipacionRelevanteService._validar_fecha("2009-12-31")
        self.assertIn("fecha", caught.exception.details["fields"])

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("extension.db.session.add")
        self.commit_patcher = patch("extension.db.session.commit")
        self.rollback_patcher = patch("extension.db.session.rollback")
        self.get_patcher = patch("modules.memorias.services.memoria_service.db.session.get")

        self.mock_add = self.add_patcher.start()
        self.mock_commit = self.commit_patcher.start()
        self.mock_rollback = self.rollback_patcher.start()
        self.mock_get = self.get_patcher.start()

        self.addCleanup(self.add_patcher.stop)
        self.addCleanup(self.commit_patcher.stop)
        self.addCleanup(self.rollback_patcher.stop)
        self.addCleanup(self.get_patcher.stop)

    def test_snapshot_participacion_relevante_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=25,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        participacion = SimpleNamespace(
            id=7,
            nombre_evento="Congreso A",
            forma_participacion="panelista",
            fecha=date(2026, 4, 20),
            investigador_id=4,
            becario_id=None,
            investigador=SimpleNamespace(nombre_apellido="Ana Perez"),
            becario=None,
        )
        with patch(
            "modules.proyectos.services.participacion_relevante_service.consultar_entidades_memoria",
            side_effect=[[participacion], []],
        ):
            snapshots = ParticipacionRelevanteService.snapshot_para_memoria_version(
                version,
                user_id=14
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].participacion_relevante_id, 7)
        self.assertEqual(snapshots[0].investigador_nombre, "Ana Perez")
        self.assertIsNone(snapshots[0].becario_id)
        self.assertEqual(snapshots[0].created_by, 14)
        self.mock_add.assert_called()

    def test_valida_becario_como_participante(self):
        becario = SimpleNamespace(id=9, activo=True, deleted_at=None)
        with patch(
            "modules.proyectos.services.participacion_relevante_service.db.session.get",
            return_value=becario,
        ) as get:
            rol, participante_id, participante = (
                ParticipacionRelevanteService._validar_participante(
                    {"participante": {"rol": "becario", "id": 9}}
                )
            )

        self.assertEqual((rol, participante_id), ("becario", 9))
        self.assertIs(participante, becario)
        self.assertEqual(get.call_args.args[1], 9)

    def test_ids_iguales_conservan_identidad_por_rol(self):
        investigador = SimpleNamespace(id=5, activo=True, deleted_at=None)
        becario = SimpleNamespace(id=5, activo=True, deleted_at=None)
        with patch(
            "modules.proyectos.services.participacion_relevante_service.db.session.get",
            side_effect=[investigador, becario],
        ):
            referencia_investigador = ParticipacionRelevanteService._validar_participante(
                {"participante": {"rol": "investigador", "id": 5}}
            )
            referencia_becario = ParticipacionRelevanteService._validar_participante(
                {"participante": {"rol": "becario", "id": 5}}
            )

        self.assertEqual(referencia_investigador[:2], ("investigador", 5))
        self.assertEqual(referencia_becario[:2], ("becario", 5))

    def test_create_asocia_becario_sin_investigador(self):
        creado = None

        def construir(**datos):
            nonlocal creado
            creado = SimpleNamespace(
                **datos,
                serialize=lambda: {
                    "participante": {"rol": "becario", "id": datos["becario_id"]}
                },
            )
            return creado

        becario = SimpleNamespace(id=12, activo=True, deleted_at=None)
        payload = {
            "nombre_evento": "Encuentro institucional",
            "forma_participacion": "panelista",
            "fecha": "2026-04-20",
            "participante": {"rol": "becario", "id": 12},
        }
        with patch(
            "modules.proyectos.services.participacion_relevante_service.db.session.get",
            return_value=becario,
        ), patch.object(
            ParticipacionRelevanteService, "_validar_no_duplicado"
        ), patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevante",
            side_effect=construir,
        ):
            resultado = ParticipacionRelevanteService.create(payload, user_id=1)

        self.assertEqual(resultado["participante"], {"rol": "becario", "id": 12})
        self.assertIsNone(creado.investigador_id)
        self.assertEqual(creado.becario_id, 12)

    def test_change_status_a_cerrada_genera_snapshot_participaciones_relevantes(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=6,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.EN_REVISION,
            created_by=1
        )
        version.deleted_at = None
        memoria.deleted_at = None
        memoria.version_actual = version
        memoria.version_actual_id = version.id
        memoria.versiones = [version]
        self.mock_get.return_value = memoria

        with patch(
            "modules.memorias.services.memoria_service.snapshot_investigadores_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.snapshot_becarios_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.snapshot_personal_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.ProyectoInvestigacionService.snapshot_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.ActividadDocenciaService.snapshot_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.ParticipacionRelevanteService.snapshot_para_memoria_version"
        ) as mock_snapshot:
            with patch(
                "modules.memorias.services.memoria_service.DocumentacionBibliograficaService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.EquipamientoService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.MovimientoFinancieroService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.TransferenciaSocioProductivaService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.TrabajoReunionCientificaService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.TrabajosRevistasReferatoService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.DistincionRecibidaService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.RegistrosPropiedadService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.ArticuloDivulgacionService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.snapshot_visitas_para_memoria_version"
            ):
                resultado = MemoriaService.change_status(
                    1,
                    {"estado": "cerrada"},
                    user_id=71
                )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 71)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_participacion_relevante_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="participacion_relevante",
            registro_id=7,
            campo="forma_participacion",
            valor_anterior="panelista",
            valor_nuevo="expositor",
            fecha_cambio=datetime(2026, 4, 23, 10, 0, 0),
            usuario_id=3
        )
        auditoria.usuario = SimpleNamespace(nombre_usuario="admin")

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [auditoria])
            )
        )

        with patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevanteService._get_or_404",
            return_value=SimpleNamespace(id=7)
        ), patch(
            "modules.shared.services.auditoria_service.AuditoriaCampo",
            new=SimpleNamespace(
                query=fake_query,
                entidad=None,
                registro_id=None,
                fecha_cambio=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            historial = ParticipacionRelevanteService.get_historial(7)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "forma_participacion")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_participacion_relevante_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "participacion_relevante_id": 7,
                "nombre_evento": "Congreso A",
                "memoria_version_id": 25
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevanteMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                fecha=SimpleNamespace(desc=lambda: None)
            )
        ):
            resultado = ParticipacionRelevanteService.obtener_snapshots_por_memoria_version(25)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["participacion_relevante_id"], 7)
        self.assertEqual(resultado[0]["memoria_version_id"], 25)


class ParticipacionRelevanteMigracionTestCase(unittest.TestCase):
    def test_upgrade_preserva_investigadores_y_admite_becarios(self):
        ruta = (
            Path(__file__).resolve().parents[1]
            / "migrations/versions/c35e8a1b7d42_participaciones_relevantes_con_becarios.py"
        )
        spec = importlib.util.spec_from_file_location("iss35_migration", ruta)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = sa.create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE investigador (id INTEGER PRIMARY KEY)")
            conn.exec_driver_sql("CREATE TABLE becario (id INTEGER PRIMARY KEY)")
            conn.exec_driver_sql("INSERT INTO investigador VALUES (1)")
            conn.exec_driver_sql("INSERT INTO becario VALUES (1)")
            conn.exec_driver_sql(
                "CREATE TABLE participacion_relevante ("
                "id INTEGER PRIMARY KEY, investigador_id INTEGER, "
                "CONSTRAINT fk_participacion_investigador FOREIGN KEY(investigador_id) REFERENCES investigador(id))"
            )
            conn.exec_driver_sql(
                "CREATE TABLE participacion_relevante_memoria_version ("
                "id INTEGER PRIMARY KEY, investigador_id INTEGER NOT NULL, investigador_nombre VARCHAR(255), "
                "CONSTRAINT fk_participacion_memoria_investigador FOREIGN KEY(investigador_id) REFERENCES investigador(id))"
            )
            conn.exec_driver_sql("INSERT INTO participacion_relevante VALUES (1, 1)")
            conn.exec_driver_sql(
                "INSERT INTO participacion_relevante_memoria_version VALUES (1, 1, 'Ana')"
            )

            operations = Operations(MigrationContext.configure(conn))
            with patch.object(migration, "op", operations):
                migration.upgrade()
                self.assertEqual(
                    conn.exec_driver_sql(
                        "SELECT investigador_id FROM participacion_relevante WHERE id = 1"
                    ).scalar(),
                    1,
                )
                conn.exec_driver_sql(
                    "INSERT INTO participacion_relevante (id, investigador_id, becario_id) VALUES (2, NULL, 1)"
                )
                conn.exec_driver_sql(
                    "INSERT INTO participacion_relevante_memoria_version "
                    "(id, investigador_id, becario_id, becario_nombre) VALUES (2, NULL, 1, 'Luis')"
                )
                with self.assertRaises(sa.exc.IntegrityError):
                    conn.exec_driver_sql(
                        "INSERT INTO participacion_relevante (id, investigador_id, becario_id) VALUES (3, 1, 1)"
                    )
                migration.downgrade()

            self.assertEqual(
                conn.exec_driver_sql("SELECT COUNT(*) FROM participacion_relevante").scalar(), 1
            )
            self.assertNotIn(
                "becario_id",
                [column["name"] for column in sa.inspect(conn).get_columns("participacion_relevante")],
            )


if __name__ == "__main__":
    unittest.main()
