import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService
from modules.memorias.services.memoria_service import MemoriaService


class ActividadDocenciaMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.produccion.services.actividad_docencia_service.db.session.add")
        self.flush_patcher = patch("modules.produccion.services.actividad_docencia_service.db.session.flush")
        self.commit_patcher = patch("extension.db.session.commit")
        self.rollback_patcher = patch("extension.db.session.rollback")
        self.get_patcher = patch("modules.memorias.services.memoria_service.db.session.get")

        self.mock_add = self.add_patcher.start()
        self.mock_flush = self.flush_patcher.start()
        self.mock_commit = self.commit_patcher.start()
        self.mock_rollback = self.rollback_patcher.start()
        self.mock_get = self.get_patcher.start()

        self.addCleanup(self.add_patcher.stop)
        self.addCleanup(self.flush_patcher.stop)
        self.addCleanup(self.commit_patcher.stop)
        self.addCleanup(self.rollback_patcher.stop)
        self.addCleanup(self.get_patcher.stop)

    @patch("modules.produccion.services.actividad_docencia_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_actividad_docencia_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=21,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        grado_activo = SimpleNamespace(id=8, nombre="Titular")
        actividad = SimpleNamespace(
            id=3,
            curso="Curso A",
            institucion="UTN",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 7, 1),
            investigador_id=4,
            investigador=SimpleNamespace(nombre_apellido="Ana Perez"),
            rol_actividad_id=5,
            rol_actividad=SimpleNamespace(nombre="Responsable"),
            investigadores_grado=[
                SimpleNamespace(
                    id=9,
                    investigador_id=4,
                    grado_academico_id=8,
                    fecha_inicio=date(2026, 3, 1),
                    fecha_fin=None,
                    grado_academico=grado_activo
                ),
                SimpleNamespace(
                    id=10,
                    investigador_id=4,
                    grado_academico_id=6,
                    fecha_inicio=date(2026, 1, 1),
                    fecha_fin=date(2026, 2, 28),
                    grado_academico=SimpleNamespace(id=6, nombre="Adjunto")
                )
            ]
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [actividad])
        )

        with patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocencia",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = ActividadDocenciaService.snapshot_para_memoria_version(
                version,
                user_id=33
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].actividad_docencia_id, 3)
        self.assertEqual(snapshots[0].grado_academico_id, 8)
        self.assertEqual(snapshots[0].grado_academico_nombre, "Titular")
        self.assertEqual(len(snapshots[0].historial_grados), 2)
        self.assertEqual(
            snapshots[0].historial_grados[0].investigador_actividad_grado_id,
            9
        )
        self.assertEqual(snapshots[0].created_by, 33)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_docencia(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=5,
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
        ) as mock_snapshot, patch(
            "modules.memorias.services.memoria_service.ParticipacionRelevanteService.snapshot_para_memoria_version"
        ), patch(
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
                user_id=66
            )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 66)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_snapshots_docencia_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "actividad_docencia_id": 3,
                "curso": "Curso A",
                "memoria_version_id": 21,
                "historial_grados": [
                    {
                        "investigador_actividad_grado_id": 9,
                        "grado_academico_nombre": "Titular"
                    }
                ]
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                curso=SimpleNamespace(asc=lambda: None)
            )
        ):
            resultado = ActividadDocenciaService.obtener_snapshots_por_memoria_version(21)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["actividad_docencia_id"], 3)
        self.assertEqual(resultado[0]["memoria_version_id"], 21)
        self.assertEqual(
            resultado[0]["historial_grados"][0]["investigador_actividad_grado_id"],
            9
        )


if __name__ == "__main__":
    unittest.main()
