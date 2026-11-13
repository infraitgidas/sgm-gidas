import unittest
from datetime import date, datetime

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.services.becario_service import crear_becario
from modules.recursos.models.becas import Beca, Beca_Becario


class BecarioEdicionBecasTest(unittest.TestCase):
    setUp = fixtures.PersonalAltaPTAATest.setUp
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload
    headers = {"Authorization": "Bearer test"}

    def crear(self):
        return crear_becario(self.payload(tipo_formacion_id=1), 1)

    def consultar(self, becario):
        response = self.client.get(f"/api/v1/personal/becario/{becario.id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_sin_beca_devuelve_coleccion_vacia(self):
        self.assertEqual(self.consultar(self.crear())["becas"], [])

    def test_devuelve_datos_de_vinculos_no_eliminados_incluso_vencidos(self):
        becario = self.crear()
        for index in range(1, 5):
            db.session.add(Beca(id=index, nombre_beca=f"Beca {index}", descripcion="Descripción"))
        db.session.flush()
        for index in range(1, 5):
            db.session.add(Beca_Becario(
                id=100 + index, id_becario=becario.id, id_beca=index,
                fecha_inicio=date(2025, 1, 1),
                fecha_fin=date(2025, 12, 31) if index != 2 else None,
                monto_percibido=0 if index == 1 else None,
                deleted_at=datetime(2026, 1, 1) if index == 3 else None,
            ))
        db.session.get(Beca, 4).deleted_at = datetime(2026, 1, 1)
        db.session.commit()
        self.assertEqual(self.consultar(becario)["becas"], [
            {"id": 1, "nombre_beca": "Beca 1", "descripcion": "Descripción",
             "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-31", "monto_percibido": 0},
            {"id": 2, "nombre_beca": "Beca 2", "descripcion": "Descripción",
             "fecha_inicio": "2025-01-01", "fecha_fin": None, "monto_percibido": None},
        ])

    def test_editar_otro_campo_conserva_vinculo_sin_historial_relacional_nuevo(self):
        db.session.add(Beca(id=1, nombre_beca="Beca de formación"))
        db.session.commit()
        becario = crear_becario(self.payload(tipo_formacion_id=1, becas=[{
            "beca_id": 1, "fecha_inicio": "2026-09-01", "fecha_fin": "2027-09-01",
            "monto_percibido": 1234.50,
        }]), 1)
        before = self.consultar(becario)["becas"]
        vinculo = Beca_Becario.query.one()
        updated_at = vinculo.updated_at
        response = self.client.put(f"/api/v1/personal/becario/{becario.id}",
            json={"horas_semanales": 21}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.consultar(becario)["becas"], before)
        self.assertEqual(Beca_Becario.query.count(), 1)
        self.assertEqual(vinculo.updated_at, updated_at)
        self.assertIsNone(vinculo.deleted_at)


if __name__ == "__main__":
    unittest.main()
