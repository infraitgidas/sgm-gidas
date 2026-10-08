import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules import models_registry  # noqa: F401
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService
from modules.memorias.services.memoria_service import MemoriaService


class DocumentacionMemoriaHistorialTestCase(unittest.TestCase):

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.produccion.services.documentacion_service.db.session.add")
        self.flush_patcher = patch("modules.produccion.services.documentacion_service.db.session.flush")
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

    @patch("modules.produccion.services.documentacion_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_documentacion_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=31,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        documento = SimpleNamespace(
            id=9,
            titulo="manual de laboratorio",
            editorial="editorial utn",
            anio=2026,
            fecha=date(2026, 3, 10),
            grupo_id=4,
            grupo_utn=SimpleNamespace(nombre_unidad_academica="UTN FRBA"),
            autores=[
                SimpleNamespace(id=1, nombre_apellido="Ana Perez"),
                SimpleNamespace(id=2, nombre_apellido="Luis Diaz")
            ]
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [documento])
        )

        with patch(
            "modules.produccion.services.documentacion_service.DocumentacionBibliografica",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = DocumentacionBibliograficaService.snapshot_para_memoria_version(
                version,
                user_id=22
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].documentacion_bibliografica_id, 9)
        self.assertEqual(snapshots[0].grupo_nombre, "UTN FRBA")
        self.assertEqual(len(snapshots[0].autores_snapshot), 2)
        self.assertEqual(snapshots[0].autores_snapshot[0].autor_id, 1)
        self.assertEqual(snapshots[0].created_by, 22)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_documentacion(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=7,
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
        ) as mock_snapshot:
            with patch(
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
                    user_id=81
                )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 81)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_documentacion_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="documentacion_bibliografica",
            registro_id=9,
            campo="titulo",
            valor_anterior="manual a",
            valor_nuevo="manual b",
            fecha_cambio=datetime(2026, 4, 23, 10, 0, 0),
            usuario_id=3
        )
        auditoria.usuario = SimpleNamespace(nombre_usuario="admin")

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(
                    filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [auditoria])
                )
            )
        )

        with patch(
            "modules.produccion.services.documentacion_service.db.session.get",
            return_value=SimpleNamespace(id=9)
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
            historial = DocumentacionBibliograficaService.get_historial(9)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "titulo")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_documentacion_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "documentacion_bibliografica_id": 9,
                "titulo": "manual de laboratorio",
                "memoria_version_id": 31,
                "autores": [{"autor_id": 1}]
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.produccion.services.documentacion_service.DocumentacionBibliograficaMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                titulo=SimpleNamespace(asc=lambda: None)
            )
        ):
            resultado = DocumentacionBibliograficaService.obtener_snapshots_por_memoria_version(31)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["documentacion_bibliografica_id"], 9)
        self.assertEqual(resultado[0]["memoria_version_id"], 31)
        self.assertEqual(resultado[0]["autores"][0]["autor_id"], 1)


if __name__ == "__main__":
    unittest.main()
