import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.recursos.services.erogacion_service import ErogacionService
from modules.memorias.services.memoria_service import MemoriaService


class ErogacionMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.recursos.services.erogacion_service.db.session.add")
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

    @patch("modules.recursos.services.erogacion_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_erogacion_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=51,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        erogacion = SimpleNamespace(
            id=6,
            numero_erogacion=100,
            egresos=500.0,
            ingresos=100.0,
            fecha=date(2026, 3, 15),
            tipo_erogacion_id=2,
            tipo_erogacion=SimpleNamespace(nombre="Viaticos"),
            fuente_financiamiento_id=3,
            fuente_financiamiento=SimpleNamespace(nombre="UTN"),
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS")
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [erogacion])
        )

        with patch(
            "modules.recursos.services.erogacion_service.Erogacion",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = ErogacionService.snapshot_para_memoria_version(
                version,
                user_id=18
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].erogacion_id, 6)
        self.assertEqual(snapshots[0].tipo_erogacion_nombre, "Viaticos")
        self.assertEqual(snapshots[0].created_by, 18)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_erogaciones(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=9,
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
        ) as mock_snapshot:
            with patch(
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
                    user_id=93
                )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 93)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_erogacion_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="erogacion",
            registro_id=6,
            campo="egresos",
            valor_anterior=400.0,
            valor_nuevo=500.0,
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
            "modules.recursos.services.erogacion_service.db.session.get",
            return_value=SimpleNamespace(id=6)
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
            historial = ErogacionService.get_historial(6)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "egresos")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_erogacion_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "erogacion_id": 6,
                "numero_erogacion": 100,
                "memoria_version_id": 51
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.recursos.services.erogacion_service.ErogacionMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                fecha=SimpleNamespace(desc=lambda: None)
            )
        ):
            resultado = ErogacionService.obtener_snapshots_por_memoria_version(51)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["erogacion_id"], 6)
        self.assertEqual(resultado[0]["memoria_version_id"], 51)


if __name__ == "__main__":
    unittest.main()
