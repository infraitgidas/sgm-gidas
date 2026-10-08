import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.memorias.services.memoria_service import MemoriaService


class EquipamientoMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.recursos.services.equipamiento_service.db.session.add")
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

    @patch("modules.recursos.services.equipamiento_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_equipamiento_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=41,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        equipamiento = SimpleNamespace(
            id=5,
            denominacion="Microscopio",
            descripcion_breve="Equipo optico",
            fecha_incorporacion=date(2026, 2, 1),
            monto_invertido=1200.0,
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS")
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [equipamiento])
        )

        with patch(
            "modules.recursos.services.equipamiento_service.Equipamiento",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = EquipamientoService.snapshot_para_memoria_version(
                version,
                user_id=17
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].equipamiento_id, 5)
        self.assertEqual(snapshots[0].grupo_utn_nombre, "GIDAS")
        self.assertEqual(snapshots[0].created_by, 17)
        self.mock_add.assert_called()

    def test_snapshot_equipamiento_incluye_si_estuvo_activo_durante_el_periodo(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=2,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=42,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        version.memoria = memoria

        equipamiento_en_periodo = SimpleNamespace(
            id=5,
            denominacion="Microscopio",
            descripcion_breve="Equipo optico",
            fecha_incorporacion=date(2025, 11, 20),
            deleted_at=datetime(2026, 2, 10, 10, 0, 0),
            monto_invertido=1200.0,
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS")
        )
        equipamiento_fuera_periodo = SimpleNamespace(
            id=6,
            denominacion="Servidor viejo",
            descripcion_breve="Infraestructura anterior",
            fecha_incorporacion=date(2025, 11, 20),
            deleted_at=datetime(2025, 12, 20, 10, 0, 0),
            monto_invertido=800.0,
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS")
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                all=lambda: [equipamiento_en_periodo, equipamiento_fuera_periodo]
            )
        )

        with patch(
            "modules.recursos.services.equipamiento_service.Equipamiento",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = EquipamientoService.snapshot_para_memoria_version(
                version,
                user_id=17
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].equipamiento_id, 5)

    def test_change_status_a_cerrada_genera_snapshot_equipamiento(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=8,
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
        ) as mock_snapshot:
            with patch(
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
                    user_id=91
                )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 91)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_equipamiento_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="equipamiento_grupo",
            registro_id=5,
            campo="denominacion",
            valor_anterior="Microscopio A",
            valor_nuevo="Microscopio B",
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
            "modules.recursos.services.equipamiento_service.db.session.get",
            return_value=SimpleNamespace(id=5)
        ), patch(
            "modules.shared.services.auditoria_service.AuditoriaCampo",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                entidad=None,
                registro_id=None,
                fecha_cambio=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            historial = EquipamientoService.get_historial(5)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "denominacion")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_equipamiento_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "equipamiento_id": 5,
                "denominacion": "Microscopio",
                "memoria_version_id": 41
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.recursos.services.equipamiento_service.EquipamientoMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                denominacion=SimpleNamespace(asc=lambda: None)
            )
        ):
            resultado = EquipamientoService.obtener_snapshots_por_memoria_version(41)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["equipamiento_id"], 5)
        self.assertEqual(resultado[0]["memoria_version_id"], 41)


if __name__ == "__main__":
    unittest.main()
