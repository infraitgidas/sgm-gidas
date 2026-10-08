import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from modules.shared.exceptions import ConflictError, ValidationError
from app import create_app
from config import Config
from extension import db
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.transferencia.models.transferencia_socio import Adoptante, TipoContrato
from modules.transferencia.services.adoptante_service import AdoptanteService
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService


class TransferenciaAutonumeroTestCase(unittest.TestCase):
    def test_alta_y_edicion_persisten_adoptantes_con_la_transferencia(self):
        config = type("TransferenciaTestConfig", (Config,), {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        with patch("app.get_config_class", return_value=config):
            app = create_app()
        with app.app_context():
            db.create_all()
            grupo = GrupoInvestigacionUtn(mail="gidas@example.org", nombre_unidad_academica="UTN", objetivo_desarrollo="Investigación", nombre_sigla_grupo="GIDAS")
            tipo = TipoContrato(nombre="Convenio")
            db.session.add_all([grupo, tipo])
            db.session.commit()
            payload = {
                "denominacion": "Convenio de prueba", "demandante": "Municipalidad",
                "descripcion_actividad": "Asistencia tecnica especializada", "monto": 100.0,
                "fecha_inicio": "2026-09-01", "tipo_contrato_id": tipo.id,
                "grupo_utn_id": grupo.id, "adoptantes_ids": [],
                "adoptantes_nuevos": ["Municipalidad de Resistencia"],
            }
            creado = TransferenciaSocioProductivaService.create(payload, 1)
            self.assertEqual([item["nombre"] for item in creado["adoptantes"]], ["Municipalidad de Resistencia"])
            self.assertEqual(Adoptante.query.count(), 1)
            self.assertEqual([item["nombre"] for item in AdoptanteService.get_all()], ["Municipalidad de Resistencia"])
            self.assertEqual([item["nombre"] for item in TransferenciaSocioProductivaService.get_by_id(creado["id"])["adoptantes"]], ["Municipalidad de Resistencia"])
            primer_adoptante = Adoptante.query.filter_by(nombre="Municipalidad de Resistencia").one()
            with self.assertRaises(ConflictError):
                AdoptanteService.delete(primer_adoptante.id, 1)
            actualizado = TransferenciaSocioProductivaService.update(creado["id"], {"adoptantes_ids": [], "adoptantes_nuevos": ["Instituto Regional"]}, 1)
            self.assertEqual([item["nombre"] for item in actualizado["adoptantes"]], ["Instituto Regional"])
            self.assertEqual(Adoptante.query.count(), 2)
            with self.assertRaises(ConflictError):
                AdoptanteService.update(primer_adoptante.id, {"nombre": "Instituto Regional"}, 1)
            AdoptanteService.delete(primer_adoptante.id, 1)
            self.assertEqual([item["nombre"] for item in AdoptanteService.get_all("false")], ["Municipalidad de Resistencia"])
            self.assertEqual(len(AdoptanteService.get_all("all")), 2)
            self.assertEqual([item["nombre"] for item in AdoptanteService.get_all()], ["Instituto Regional"])
            self.assertEqual([item["campo"] for item in AdoptanteService.get_historial(primer_adoptante.id)], ["activo"])
            db.session.remove()
            db.drop_all()

    def test_alta_asigna_siguiente_numero_y_descarta_numero_del_cliente(self):
        created = []

        class FakeTransferencia:
            numero_transferencia = "numero_transferencia"

            def __init__(self, **kwargs):
                created.append(kwargs)

            def serialize(self):
                return created[-1]

        session = Mock()
        session.get_bind.return_value.dialect.name = "sqlite"
        session.get.return_value = SimpleNamespace(deleted_at=None)
        session.query.return_value.scalar.return_value = 42
        catalogo = SimpleNamespace()
        payload = {
            "numero_transferencia": 9999,
            "denominacion": "Convenio de prueba",
            "demandante": "Municipalidad",
            "descripcion_actividad": "Asistencia tecnica especializada",
            "monto": 100.0,
            "fecha_inicio": "2026-09-01",
            "tipo_contrato_id": 1,
            "grupo_utn_id": 1,
        }
        module = "modules.transferencia.services.transferencia_service"
        with patch(f"{module}.db.session", session), \
             patch(f"{module}.TransferenciaSocioProductiva", FakeTransferencia), \
             patch(f"{module}.TipoContrato", catalogo), \
             patch(f"{module}.GrupoInvestigacionUtn", catalogo):
            result = TransferenciaSocioProductivaService.create(payload, 7)

        self.assertEqual(result["numero_transferencia"], 43)
        self.assertEqual(created[0]["created_by"], 7)
        session.commit.assert_called_once()

    def test_edicion_de_tipo_de_contrato_persiste_y_audita_el_cambio(self):
        transferencia = SimpleNamespace(
            id=8, deleted_at=None, tipo_contrato_id=1,
            fecha_inicio=date(2026, 1, 1), fecha_fin=None,
            mark_updated=Mock(), serialize=lambda: {"tipo_contrato_id": 2},
        )
        tipo = SimpleNamespace(id=2, deleted_at=None)
        session = Mock()
        session.get.side_effect = [transferencia, tipo]
        module = "modules.transferencia.services.transferencia_service"
        with patch(f"{module}.db.session", session), \
             patch(f"{module}.AuditoriaService.registrar_cambios") as audit:
            result = TransferenciaSocioProductivaService.update(8, {"tipo_contrato_id": 2}, 7)
        self.assertEqual(result["tipo_contrato_id"], 2)
        self.assertEqual(transferencia.tipo_contrato_id, 2)
        transferencia.mark_updated.assert_called_once_with(7)
        self.assertEqual(audit.call_args.kwargs["cambios"]["tipo_contrato_id"], {"valor_anterior": 1, "valor_nuevo": 2})

    def test_edicion_rechaza_tipo_de_contrato_invalido(self):
        transferencia = SimpleNamespace(id=8, deleted_at=None)
        session = Mock()
        session.get.return_value = transferencia
        with patch("modules.transferencia.services.transferencia_service.db.session", session):
            with self.assertRaises(ValidationError) as caught:
                TransferenciaSocioProductivaService.update(8, {"tipo_contrato_id": "invalido"}, 7)
        self.assertIn("tipo_contrato_id", caught.exception.details["fields"])
        session.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
