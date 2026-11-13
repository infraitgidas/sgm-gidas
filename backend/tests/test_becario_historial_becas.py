import json
import unittest

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.services.becario_service import crear_becario, actualizar_becario
from modules.recursos.models.becas import Beca
from modules.shared.models.auditoria_campo import AuditoriaCampo


class BecarioHistorialBecasTest(unittest.TestCase):
    setUp = fixtures.PersonalAltaPTAATest.setUp
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload

    def historial(self, becario):
        response = self.client.get(f"/api/v1/personal/becario/{becario.id}/historial",
                                   headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_monto_y_fecha_de_fin_quedan_disponibles_para_el_resumen(self):
        db.session.add(Beca(id=1, nombre_beca="Beca doctoral"))
        db.session.commit()
        vinculo = {"beca_id": 1, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-01", "monto_percibido": 1000}
        becario = crear_becario(self.payload(tipo_formacion_id=1, becas=[vinculo]), 1)
        actualizar_becario(becario.id, {"becas": [{**vinculo, "fecha_fin": "2027-03-01", "monto_percibido": 0}]}, 1)
        rows = [row for row in self.historial(becario) if row["campo"] == "becas"]
        self.assertEqual([row["valor_nuevo"]["accion"] for row in rows], ["actualizar", "vincular"])
        self.assertEqual(rows[0]["valor_nuevo"]["detalle"]["fecha_fin"], "2027-03-01")
        self.assertEqual(rows[0]["valor_nuevo"]["detalle"]["monto_percibido"], 0)

    def test_lectura_conserva_valores_historicos_sin_reescribir_auditoria(self):
        becario = crear_becario(self.payload(tipo_formacion_id=1), 1)
        values = [json.dumps({"accion": "actualizar", "detalle": {"beca_id": 1, "monto_percibido": 50}}),
                  "{JSON incompleto", {"estructura_anterior": [1]}]
        rows = [AuditoriaCampo(entidad="becario", registro_id=becario.id, campo="becas", valor_nuevo=value) for value in values]
        db.session.add_all(rows)
        db.session.commit()
        expected = {row.id: row.valor_nuevo for row in rows}
        result = self.historial(becario)
        self.assertEqual({row["id"]: row["valor_nuevo"] for row in result if row["id"] in expected}, expected)
        db.session.expire_all()
        self.assertEqual({row.id: row.valor_nuevo for row in AuditoriaCampo.query.filter(AuditoriaCampo.id.in_(expected)).all()}, expected)


if __name__ == "__main__":
    unittest.main()
