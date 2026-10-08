import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.memorias.services.memoria_service import MemoriaService
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService


class ProyectoMemoriaHistorialTestCase(unittest.TestCase):

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

    @patch("modules.proyectos.services.proyecto_investigacion_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_proyecto_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=15,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        proyecto = SimpleNamespace(
            id=4,
            codigo_proyecto="LPSIEC1347",
            nombre_proyecto="Proyecto A",
            descripcion_proyecto="Descripcion",
            logros_obtenidos="Modelo experimental validado",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=None,
            dificultades_proyecto="Ninguna",
            monto_destinado=1000.0,
            tipo_proyecto_id=2,
            grupo_utn_id=3,
            fuente_financiamiento_id=4,
            tipo_proyecto=SimpleNamespace(nombre="PID"),
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS"),
            fuente_financiamiento=SimpleNamespace(nombre="UTN")
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [proyecto])
        )

        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacion",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = ProyectoInvestigacionService.snapshot_para_memoria_version(
                version,
                user_id=41
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].proyecto_investigacion_id, 4)
        self.assertEqual(snapshots[0].codigo_proyecto, "LPSIEC1347")
        self.assertEqual(snapshots[0].tipo_proyecto_nombre, "PID")
        self.assertEqual(snapshots[0].grupo_utn_nombre, "GIDAS")
        self.assertEqual(snapshots[0].created_by, 41)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_proyectos(self):
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
        ) as mock_snapshot, patch(
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

    def test_obtener_historial_proyecto_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="proyecto_investigacion",
            registro_id=4,
            campo="nombre_proyecto",
            valor_anterior="Proyecto A",
            valor_nuevo="Proyecto B",
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
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacionService._get_proyecto_or_404",
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
            historial = ProyectoInvestigacionService.obtener_historial(4)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "nombre_proyecto")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_proyecto_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "proyecto_investigacion_id": 4,
                "nombre_proyecto": "Proyecto A",
                "memoria_version_id": 15
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacionMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                nombre_proyecto=SimpleNamespace(asc=lambda: None)
            )
        ):
            resultado = ProyectoInvestigacionService.obtener_snapshots_por_memoria_version(15)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["proyecto_investigacion_id"], 4)
        self.assertEqual(resultado[0]["memoria_version_id"], 15)
