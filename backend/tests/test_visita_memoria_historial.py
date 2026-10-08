import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.memorias.services.memoria_service import MemoriaService
from modules.grupo.services.visita_service import (
    crear_visita_academica,
    obtener_historial_visita,
    obtener_snapshots_visitas_por_memoria_version,
    snapshot_visitas_para_memoria_version,
)
from modules.shared.exceptions import ValidationError


class VisitaMemoriaHistorialTestCase(unittest.TestCase):

    def test_tipo_visita_invalido_identifica_el_campo_sin_persistir(self):
        with patch("modules.grupo.services.visita_service.db.session.add") as add:
            with self.assertRaises(ValidationError) as caught:
                crear_visita_academica({"tipo_visita_id": 0})
            self.assertEqual(caught.exception.details["fields"], {
                "tipo_visita_id": "Seleccione un tipo de visita válido."
            })
            add.assert_not_called()

    def test_fecha_invalida_identifica_el_campo_sin_persistir(self):
        from modules.grupo.services.visita_service import _validar_fecha

        with self.assertRaises(ValidationError) as caught:
            _validar_fecha("2026-99-99")
        self.assertEqual(caught.exception.details["fields"], {
            "fecha": "Ingrese una fecha válida."
        })

        with self.assertRaises(ValidationError) as fuera_de_rango:
            _validar_fecha("2009-12-31")
        self.assertIn("fecha", fuera_de_rango.exception.details["fields"])

    def setUp(self):
        self.enterContext(patch("modules.memorias.services.memoria_service.MemoriaService._validar_grupo", return_value=1))
        self.enterContext(patch("modules.memorias.services.memoria_service.snapshot_contexto_institucional", return_value=None))
        self.add_patcher = patch("modules.grupo.services.visita_service.db.session.add")
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

    @patch("modules.grupo.services.visita_service.consultar_entidades_memoria", new=lambda model, version, **kwargs: model.query.filter().all())
    def test_snapshot_visitas_para_memoria_version_persiste_foto(self):
        version = MemoriaVersion(
            id=121,
            numero_version=1,
            fecha_apertura=datetime(2026, 1, 1, 0, 0, 0),
            estado=EstadoMemoria.CERRADA,
            created_by=1
        )
        visita = SimpleNamespace(
            id=8,
            razon="Intercambio academico",
            procedencia="Universidad Nacional",
            fecha=date(2026, 4, 18),
            tipo_visita_id=2,
            tipo_visita=SimpleNamespace(nombre="Institucional"),
            grupo_utn_id=4,
            grupo_utn=SimpleNamespace(nombre_sigla_grupo="GIDAS")
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: [visita])
        )

        with patch(
            "modules.grupo.services.visita_service.VisitaAcademica",
            new=SimpleNamespace(
                query=fake_query,
                deleted_at=SimpleNamespace(is_=lambda *_: None)
            )
        ):
            snapshots = snapshot_visitas_para_memoria_version(version, user_id=28)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].visita_academica_id, 8)
        self.assertEqual(snapshots[0].tipo_visita_nombre, "Institucional")
        self.assertEqual(snapshots[0].grupo_utn_nombre, "GIDAS")
        self.assertEqual(snapshots[0].created_by, 28)
        self.mock_add.assert_called()

    def test_change_status_a_cerrada_genera_snapshot_visitas(self):
        memoria = Memoria(
            grupo_utn_id=1,
            id=1,
            periodo_inicio=date(2026, 1, 1),
            periodo_fin=date(2026, 12, 31),
            created_by=1
        )
        version = MemoriaVersion(
            id=16,
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
        ), patch(
            "modules.memorias.services.memoria_service.RegistrosPropiedadService.snapshot_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.ArticuloDivulgacionService.snapshot_para_memoria_version"
        ), patch(
            "modules.memorias.services.memoria_service.snapshot_visitas_para_memoria_version"
        ) as mock_snapshot:
            resultado = MemoriaService.change_status(
                1,
                {"estado": "cerrada"},
                user_id=102
            )

        self.assertEqual(version.estado, EstadoMemoria.CERRADA)
        mock_snapshot.assert_called_once_with(version, 102)
        self.assertEqual(resultado["version_actual"]["estado"], "cerrada")

    def test_obtener_historial_visita_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="visita_academica",
            registro_id=8,
            campo="procedencia",
            valor_anterior="Institucion A",
            valor_nuevo="Institucion B",
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
            "modules.grupo.services.visita_service.db.session.get",
            return_value=SimpleNamespace(id=8)
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
            historial = obtener_historial_visita(8)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "procedencia")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")

    def test_obtener_snapshots_visitas_por_memoria_version(self):
        snapshot = SimpleNamespace(
            serialize=lambda: {
                "visita_academica_id": 8,
                "razon": "Intercambio academico",
                "memoria_version_id": 121
            }
        )

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [snapshot])
            )
        )

        with patch(
            "modules.grupo.services.visita_service.VisitaAcademicaMemoriaVersion",
            new=SimpleNamespace(
                query=fake_query,
                memoria_version_id=None,
                deleted_at=SimpleNamespace(is_=lambda *_: None),
                fecha=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            resultado = obtener_snapshots_visitas_por_memoria_version(121)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["visita_academica_id"], 8)
        self.assertEqual(resultado[0]["memoria_version_id"], 121)


if __name__ == "__main__":
    unittest.main()
