import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.memorias.services.memoria_service import MemoriaService
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService


class TransferenciaMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.transferencia.services.transferencia_service.db.session.add")
        self.flush_patcher = patch("modules.transferencia.services.transferencia_service.db.session.flush")
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

    @patch("modules.transferencia.services.transferencia_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_transferencia_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=61,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        transferencia = SimpleNamespace(
            id=7,
            numero_transferencia=300,
            denominacion="Transferencia con pyme",
            demandante="Empresa A",
            descripcion_actividad="Asistencia tecnica especializada",
            monto=2500.0,
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 8, 1),
            tipo_contrato_id=2,
            tipo_contrato_transferencia=SimpleNamespace(nombre="Convenio"),
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS"),
            participaciones=[
                SimpleNamespace(
                    id=10,
                    deleted_at=None,
                    adoptante=SimpleNamespace(
                        id=3,
                        deleted_at=None,
                        nombre="Empresa A"
                    )
                ),
                SimpleNamespace(
                    id=11,
                    deleted_at=None,
                    adoptante=SimpleNamespace(
                        id=4,
                        deleted_at=None,
                        nombre="Empresa B"
                    )
                )
            ]
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [transferencia])
        )

        with patch(
            "modules.transferencia.services.transferencia_service.TransferenciaSocioProductiva",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = TransferenciaSocioProductivaService.snapshot_para_memoria_version(
                version,
                user_id=19
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].transferencia_id, 7)
        self.assertEqual(snapshots[0].tipo_contrato_nombre, "Convenio")
        self.assertEqual(len(snapshots[0].adoptantes_snapshot), 2)
        self.assertEqual(snapshots[0].adoptantes_snapshot[0].adoptante_id, 3)
        self.assertEqual(snapshots[0].created_by, 19)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_transferencias(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=10,
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
        ) as mock_snapshot, patch(
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
                user_id=94
            )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 94)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_transferencia_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="transferencia_socio_productiva",
            registro_id=7,
            campo="monto",
            valor_anterior=1000.0,
            valor_nuevo=2500.0,
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
            "modules.transferencia.services.transferencia_service.db.session.get",
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
            historial = TransferenciaSocioProductivaService.get_historial(7)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "monto")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_transferencia_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "transferencia_id": 7,
                "numero_transferencia": 300,
                "memoria_version_id": 61
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.transferencia.services.transferencia_service.TransferenciaSocioProductivaMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                fecha_inicio=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            resultado = TransferenciaSocioProductivaService.obtener_snapshots_por_memoria_version(61)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["transferencia_id"], 7)
        self.assertEqual(resultado[0]["memoria_version_id"], 61)


if __name__ == "__main__":
    unittest.main()
