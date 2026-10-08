import unittest
from datetime import date
from unittest.mock import patch

from modules import models_registry  # noqa: F401
from modules.personal.models.personal import Becario
from modules.personal.services.becario_service import _sincronizar_becas
from modules.recursos.models.becas import Beca, Beca_Becario


class PersonalRelacionesConsolidadasTestCase(unittest.TestCase):

    def test_sincroniza_altas_bajas_y_cambios_sin_commits_intermedios(self):
        becario = Becario(id=7, nombre_apellido="Becario", horas_semanales=20)
        existente = Beca_Becario(
            id=10,
            id_beca=1,
            id_becario=7,
            fecha_inicio=date(2025, 1, 1),
            monto_percibido=100,
            created_by=1,
        )
        removida = Beca_Becario(
            id=11,
            id_beca=2,
            id_becario=7,
            fecha_inicio=date(2025, 1, 1),
            created_by=1,
        )
        becario.becas = [existente, removida]
        becas = {
            1: Beca(id=1, nombre_beca="A", created_by=1),
            2: Beca(id=2, nombre_beca="B", created_by=1),
            3: Beca(id=3, nombre_beca="C", created_by=1),
        }
        for beca in becas.values():
            beca.deleted_at = None

        with patch("extension.db.session.get", side_effect=lambda _model, key: becas[key]), patch(
            "extension.db.session.add"
        ) as add, patch(
            "modules.personal.services.becario_service.AuditoriaService.registrar_evento_relacion"
        ) as audit:
            _sincronizar_becas(
                becario,
                [
                    {"beca_id": 1, "fecha_inicio": "2025-02-01", "fecha_fin": "2025-12-01", "monto_percibido": 150},
                    {"beca_id": 3, "fecha_inicio": "2025-03-01", "fecha_fin": "2025-12-01"},
                ],
                user_id=9,
            )

        self.assertEqual(existente.fecha_inicio, date(2025, 2, 1))
        self.assertEqual(existente.monto_percibido, 150.0)
        self.assertIsNotNone(removida.deleted_at)
        self.assertEqual(add.call_count, 1)
        self.assertEqual(audit.call_count, 3)

    def test_rechaza_becas_repetidas(self):
        becario = Becario(id=7, nombre_apellido="Becario", horas_semanales=20)
        becario.becas = []
        beca = Beca(id=1, nombre_beca="A", created_by=1)
        beca.deleted_at = None

        with patch("extension.db.session.get", return_value=beca):
            with self.assertRaisesRegex(ValueError, "beca está repetida") as caught:
                _sincronizar_becas(
                    becario,
                    [
                        {"beca_id": 1, "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-01"},
                        {"beca_id": 1, "fecha_inicio": "2025-02-01", "fecha_fin": "2025-12-01"},
                    ],
                    user_id=9,
                )
            self.assertIn("becas", caught.exception.details["fields"])

    def test_exige_fecha_de_fin_para_registrar_el_plazo(self):
        becario = Becario(id=7, nombre_apellido="Becario", horas_semanales=20)
        becario.becas = []
        beca = Beca(id=1, nombre_beca="Beca", created_by=1)
        beca.deleted_at = None
        with patch("extension.db.session.get", return_value=beca):
            with self.assertRaisesRegex(ValueError, "fecha de fin") as caught:
                _sincronizar_becas(becario, [{"beca_id": 1, "fecha_inicio": "2025-01-01"}], 9)
        self.assertIn("becas", caught.exception.details["fields"])


if __name__ == "__main__":
    unittest.main()
