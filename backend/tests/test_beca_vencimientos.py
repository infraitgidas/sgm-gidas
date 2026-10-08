import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from flask import Flask, g

from extension import db
from modules import models_registry  # noqa: F401
from modules.personal.models.personal import Becario
from modules.recursos.models.becas import Beca, Beca_Becario
from modules.recursos.routes.becas_rutas import beca_bp
from modules.recursos.services.becas_service import BecaService


class BecaVencimientosTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(beca_bp, url_prefix="/api/v1/becas")
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_solo_vinculos_vigentes_con_menos_de_treinta_dias(self):
        hoy = date(2026, 10, 1)
        beca = Beca(id=1, nombre_beca="Investigación", fecha_alta_grupo=hoy)
        becario = Becario(id=1, nombre_apellido="Ana Pérez", horas_semanales=20, grupo_utn_id=1, tipo_formacion_id=1)
        db.session.add_all([beca, becario])
        db.session.flush()
        descartada = Beca_Becario(id=6, id_beca=1, id_becario=1, fecha_inicio=hoy - timedelta(days=90), fecha_fin=hoy + timedelta(days=1))
        descartada.deleted_at = datetime(2026, 9, 30)
        db.session.add_all([
            Beca_Becario(id=1, id_beca=1, id_becario=1, fecha_inicio=hoy - timedelta(days=90), fecha_fin=hoy),
            Beca_Becario(id=2, id_beca=1, id_becario=1, fecha_inicio=hoy - timedelta(days=90), fecha_fin=hoy + timedelta(days=29)),
            Beca_Becario(id=3, id_beca=1, id_becario=1, fecha_inicio=hoy - timedelta(days=90), fecha_fin=hoy + timedelta(days=30)),
            Beca_Becario(id=4, id_beca=1, id_becario=1, fecha_inicio=hoy - timedelta(days=90), fecha_fin=hoy - timedelta(days=1)),
            Beca_Becario(id=5, id_beca=1, id_becario=1, fecha_inicio=hoy + timedelta(days=1), fecha_fin=hoy + timedelta(days=10)),
            descartada,
        ])
        db.session.commit()

        result = BecaService.proximas_a_vencer(hoy)

        self.assertEqual([item["vinculacion_id"] for item in result], [1, 2])
        self.assertEqual([item["dias_restantes"] for item in result], [0, 29])
        self.assertEqual(result[0]["becario"], "Ana Pérez")
        self.assertEqual(result[0]["beca"], "Investigación")

    def test_endpoint_restringido_a_gestor(self):
        for role, expected in (("LECTURA", 403), ("ADMIN", 403), ("GESTOR", 200)):
            def authenticate():
                g.current_user_rol = role
                g.current_user_id = 1
                return {}, None

            with self.subTest(role=role), patch(
                "modules.shared.services.middleware._authenticate_request", side_effect=authenticate
            ), patch.object(BecaService, "proximas_a_vencer", return_value=[]):
                response = self.app.test_client().get("/api/v1/becas/proximas-a-vencer")
            self.assertEqual(response.status_code, expected)

    def test_listado_busca_en_servidor_y_limita_a_nueve(self):
        db.session.add_all([
            Beca(id=index, nombre_beca=f"Beca {index:02d}", fecha_alta_grupo=date(2025, 1, 1))
            for index in range(1, 11)
        ])
        db.session.commit()
        first, total = BecaService.get_page(1, 9, q="Beca")
        second, _ = BecaService.get_page(2, 9, q="Beca")
        filtered, filtered_total = BecaService.get_page(1, 9, q="Beca 10")
        self.assertEqual((len(first), len(second), total), (9, 1, 10))
        self.assertEqual((len(filtered), filtered_total), (1, 1))


if __name__ == "__main__":
    unittest.main()
