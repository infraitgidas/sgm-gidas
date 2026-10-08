import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from modules.recursos.models.becas import Beca
from modules.personal.models.personal import Becario, Investigador
from modules.transferencia.models.transferencia_socio import TransferenciaSocioProductiva
from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica
from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato
from modules.recursos.services.becas_service import BecaService
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService


class AuditoriaRelacionesServicesTestCase(unittest.TestCase):

    def setUp(self):
        self.commit_patcher = patch("extension.db.session.commit")
        self.rollback_patcher = patch("extension.db.session.rollback")
        self.add_patcher = patch("extension.db.session.add")

        self.commit_patcher.start()
        self.rollback_patcher.start()
        self.add_patcher.start()

        self.addCleanup(self.commit_patcher.stop)
        self.addCleanup(self.rollback_patcher.stop)
        self.addCleanup(self.add_patcher.stop)

    def test_vincular_becario_registra_evento_relacion(self):
        beca = Beca(id=1, nombre_beca="Beca", created_by=1)
        beca.deleted_at = None
        beca.updated_at = None
        beca.updated_by = None

        becario = Becario(
            id=7,
            nombre_apellido="Ana Perez",
            horas_semanales=10,
            tipo_formacion_id=1,
            grupo_utn_id=1,
            created_by=1
        )
        becario.deleted_at = None

        with patch(
            "modules.recursos.services.becas_service._get_beca_activa_or_404",
            return_value=beca
        ), patch(
            "modules.recursos.services.becas_service.db.session.get",
            return_value=becario
        ), patch(
            "modules.recursos.services.becas_service._get_relacion_activa",
            return_value=None
        ), patch(
            "modules.recursos.services.becas_service.AuditoriaService.registrar_evento_relacion"
        ) as mock_evento:
            resultado = BecaService.vincular_becario(
                1,
                {
                    "id_becario": 7,
                    "fecha_inicio": "2024-03-01",
                    "fecha_fin": "2024-12-01",
                    "monto_percibido": 1000
                },
                user_id=10
            )

        self.assertEqual(resultado["message"], "Becario vinculado correctamente.")
        self.assertEqual(beca.updated_by, 10)
        self.assertIsNotNone(beca.updated_at)
        mock_evento.assert_called_once()

    def test_desvincular_becario_registra_evento_relacion(self):
        beca = Beca(id=1, nombre_beca="Beca", created_by=1)
        beca.deleted_at = None
        beca.updated_at = None
        beca.updated_by = None

        relacion = SimpleNamespace(
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 1),
            monto_percibido=1000,
            soft_delete=lambda user_id: None
        )

        with patch(
            "modules.recursos.services.becas_service._get_relacion_activa",
            return_value=relacion
        ), patch(
            "modules.recursos.services.becas_service._get_beca_activa_or_404",
            return_value=beca
        ), patch(
            "modules.recursos.services.becas_service.AuditoriaService.registrar_evento_relacion"
        ) as mock_evento:
            resultado = BecaService.desvincular_becario(1, 7, user_id=11)

        self.assertEqual(resultado["message"], "Becario desvinculado correctamente.")
        self.assertEqual(beca.updated_by, 11)
        self.assertIsNotNone(beca.updated_at)
        mock_evento.assert_called_once()

    def test_add_adoptantes_registra_eventos_relacion(self):
        transferencia = TransferenciaSocioProductiva(
            id=2,
            numero_transferencia=20,
            denominacion="Transferencia",
            demandante="Empresa",
            descripcion_actividad="Descripcion extensa de prueba",
            monto=1200,
            fecha_inicio=date(2024, 1, 1),
            tipo_contrato_id=1,
            grupo_utn_id=1,
            created_by=1
        )
        transferencia.deleted_at = None
        transferencia.updated_at = None
        transferencia.updated_by = None

        adoptantes = [
            SimpleNamespace(id=3, nombre="Empresa A", deleted_at=None),
            SimpleNamespace(id=4, nombre="Empresa B", deleted_at=None)
        ]

        fake_query_adoptantes = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(all=lambda: adoptantes)
        )
        fake_query_participacion = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(first=lambda: None)
        )

        with patch(
            "modules.transferencia.services.transferencia_service.db.session.get",
            return_value=transferencia
        ), patch(
            "modules.transferencia.services.transferencia_service.db.session.query",
            side_effect=[
                fake_query_adoptantes,
                fake_query_participacion,
                fake_query_participacion
            ]
        ), patch(
            "modules.transferencia.services.transferencia_service.AuditoriaService.registrar_evento_relacion"
        ) as mock_evento:
            resultado = TransferenciaSocioProductivaService.add_adoptantes(
                2,
                [3, 4],
                user_id=12
            )

        self.assertEqual(resultado["id"], 2)
        self.assertEqual(transferencia.updated_by, 12)
        self.assertIsNotNone(transferencia.updated_at)
        self.assertEqual(mock_evento.call_count, 2)



if __name__ == "__main__":
    unittest.main()
