import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.personal.models.personal import Investigador
from modules.shared.services.auditoria_service import AuditoriaService
from modules.personal.services.investigador_service import (
    obtener_historial_investigador,
    obtener_snapshots_investigadores_por_memoria_version,
    snapshot_investigadores_para_memoria_version,
)
from modules.memorias.services.memoria_service import MemoriaService


class InvestigadorMemoriaHistorialTestCase(unittest.TestCase):

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

    def test_snapshot_investigadores_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=9,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        version.memoria = Memoria(
            grupo_utn_id=6,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
        )
        investigador = SimpleNamespace(
            id=5,
            nombre_apellido="Ana Perez",
            horas_semanales=20,
            fecha_alta_grupo=date(2026, 2, 1),
            tipo_dedicacion_id=2,
            categoria_utn_id=3,
            programa_incentivos_id=4,
            grupo_utn_id=6,
            tipo_dedicacion=SimpleNamespace(nombre="Exclusiva"),
            categoria_utn=SimpleNamespace(nombre="Categoria I"),
            programa_incentivos=SimpleNamespace(nombre="Programa A"),
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS"),
            historial_horas=[SimpleNamespace(id=1, horas_semanales=30, fecha_inicio=date(2020, 1, 1), fecha_fin=None)]
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [investigador])
        )

        with patch(
            "modules.personal.services.investigador_service.Investigador",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = snapshot_investigadores_para_memoria_version(
                version,
                user_id=12
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].investigador_id, 5)
        self.assertEqual(snapshots[0].horas_semanales, 30)
        self.assertEqual(snapshots[0].grupo_utn_nombre, "GIDAS")
        self.assertEqual(snapshots[0].created_by, 12)
        self.mock_add.assert_called()

    def test_snapshot_investigadores_incluye_si_estuvo_activo_durante_el_periodo(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=2,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=10,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        version.memoria = memoria

        investigador_activo_durante_periodo = SimpleNamespace(
            id=6,
            nombre_apellido="Ana Perez",
            horas_semanales=20,
            fecha_alta_grupo=date(2025, 12, 20),
            deleted_at=datetime(2026, 3, 1, 10, 0, 0),
            tipo_dedicacion_id=2,
            categoria_utn_id=3,
            programa_incentivos_id=4,
            grupo_utn_id=6,
            tipo_dedicacion=SimpleNamespace(nombre="Exclusiva"),
            categoria_utn=SimpleNamespace(nombre="Categoria I"),
            programa_incentivos=SimpleNamespace(nombre="Programa A"),
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS"),
            historial_horas=[SimpleNamespace(id=1, horas_semanales=30, fecha_inicio=date(2020, 1, 1), fecha_fin=None)]
        )
        investigador_fuera_periodo = SimpleNamespace(
            id=7,
            nombre_apellido="Luis Diaz",
            horas_semanales=15,
            fecha_alta_grupo=date(2018, 5, 10),
            deleted_at=datetime(2025, 12, 20, 10, 0, 0),
            tipo_dedicacion_id=2,
            categoria_utn_id=3,
            programa_incentivos_id=4,
            grupo_utn_id=6,
            tipo_dedicacion=SimpleNamespace(nombre="Simple"),
            categoria_utn=SimpleNamespace(nombre="Categoria II"),
            programa_incentivos=SimpleNamespace(nombre="Programa B"),
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS"),
            historial_horas=[SimpleNamespace(id=1, horas_semanales=15, fecha_inicio=date(2020, 1, 1), fecha_fin=None)]
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                all=lambda: [
                    investigador_activo_durante_periodo,
                    investigador_fuera_periodo
                ]
            )
        )

        with patch(
            "modules.personal.services.investigador_service.Investigador",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = snapshot_investigadores_para_memoria_version(
                version,
                user_id=12
            )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].investigador_id, 6)

    def test_change_status_a_cerrada_genera_snapshot_investigadores(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=2,
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
        ) as mock_snapshot, patch(
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
                user_id=99
            )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        self.assertEqual(version.updated_by, 99)
        mock_snapshot.assert_called_once_with(version, 99)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_investigador_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="investigador",
            registro_id=5,
            campo="nombre_apellido",
            valor_anterior="Ana",
            valor_nuevo="Ana Gomez",
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
            "modules.personal.services.investigador_service.obtener_investigador_por_id",
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
            historial = obtener_historial_investigador(5)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "nombre_apellido")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_investigadores_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "investigador_id": 5,
                "nombre_apellido": "Ana Perez",
                "memoria_version_id": 9
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.personal.services.investigador_service.InvestigadorMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                grupo_utn_id=1,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                nombre_apellido=SimpleNamespace(asc=lambda: None)
            )
        ):
            resultado = obtener_snapshots_investigadores_por_memoria_version(9)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["investigador_id"], 5)
        self.assertEqual(resultado[0]["memoria_version_id"], 9)


if __name__ == "__main__":
    unittest.main()
