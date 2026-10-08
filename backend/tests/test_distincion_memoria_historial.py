import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.produccion.services.distincion_service import DistincionRecibidaService
from modules.memorias.services.memoria_service import MemoriaService


class DistincionMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.produccion.services.distincion_service.db.session.add")
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

    @patch("modules.produccion.services.distincion_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_distincion_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=91,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        distincion = SimpleNamespace(
            id=4,
            fecha=date(2026, 4, 10),
            descripcion="Premio a la innovacion",
            proyecto_investigacion_id=8,
            proyecto_investigacion=SimpleNamespace(
                codigo_proyecto="LPSIEC1347",
                nombre_proyecto="Sistema GIDAS"
            )
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [distincion])
        )

        with patch(
            "modules.produccion.services.distincion_service.DistincionRecibida",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = DistincionRecibidaService.snapshot_para_memoria_version(
                version,
                user_id=25
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].distincion_id, 4)
        self.assertEqual(snapshots[0].proyecto_codigo, "LPSIEC1347")
        self.assertEqual(snapshots[0].proyecto_nombre, "Sistema GIDAS")
        self.assertEqual(snapshots[0].created_by, 25)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_distinciones(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=13,
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
        ) as mock_snapshot:
            with patch(
                "modules.memorias.services.memoria_service.RegistrosPropiedadService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.ArticuloDivulgacionService.snapshot_para_memoria_version"
            ), patch(
                "modules.memorias.services.memoria_service.snapshot_visitas_para_memoria_version"
            ):
                resultado = MemoriaService.change_status(
                    1,
                    {"estado": "cerrada"},
                    user_id=97
                )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 97)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_distincion_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="distincion_recibida",
            registro_id=4,
            campo="descripcion",
            valor_anterior="Premio",
            valor_nuevo="Premio nacional",
            fecha_cambio=datetime(2026, 4, 25, 10, 0, 0),
            usuario_id=3
        )
        auditoria.usuario = SimpleNamespace(nombre_usuario="admin")

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [auditoria])
            )
        )

        with patch(
            "modules.produccion.services.distincion_service.db.session.get",
            return_value=SimpleNamespace(id=4)
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
            historial = DistincionRecibidaService.get_historial(4)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "descripcion")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_distincion_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "distincion_id": 4,
                "descripcion": "Premio a la innovacion",
                "memoria_version_id": 91
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.produccion.services.distincion_service.DistincionRecibidaMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                fecha=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            resultado = DistincionRecibidaService.obtener_snapshots_por_memoria_version(91)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["distincion_id"], 4)
        self.assertEqual(resultado[0]["memoria_version_id"], 91)


if __name__ == "__main__":
    unittest.main()
