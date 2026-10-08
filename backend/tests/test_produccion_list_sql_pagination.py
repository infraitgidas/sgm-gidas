import unittest

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService
from modules.produccion.services.articulo_divulgacion_service import ArticuloDivulgacionService
from modules.produccion.services.distincion_service import DistincionRecibidaService
from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService
from modules.produccion.services.registro_propiedad_service import RegistrosPropiedadService
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService
from modules.proyectos.services.participacion_relevante_service import ParticipacionRelevanteService


class ProduccionListSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_listados_filtrados_cuentan_y_limitan_en_sql(self):
        cases = (
            lambda: ActividadDocenciaService.get_page({"activos": "true"}, 2, 3),
            lambda: ArticuloDivulgacionService.get_page({"activos": "true"}, 2, 3),
            lambda: DistincionRecibidaService.get_page({"activos": "true"}, 2, 3),
            lambda: DocumentacionBibliograficaService.get_page({"activos": "true"}, 2, 3),
            lambda: RegistrosPropiedadService.get_page("true", 2, 3),
            lambda: TrabajoReunionCientificaService.get_page({"activos": "true"}, 2, 3),
            lambda: TrabajosRevistasReferatoService.get_page({"activos": "true"}, 2, 3),
            lambda: ParticipacionRelevanteService.get_page({"activos": "true"}, 2, 3),
        )
        for fetch in cases:
            with self.subTest(fetch=fetch):
                statements = []

                def record(_conn, _cursor, sql, _params, _context, _many):
                    if sql.lstrip().lower().startswith("select"):
                        statements.append(sql.lower())

                event.listen(db.engine, "before_cursor_execute", record)
                try:
                    rows, total = fetch()
                finally:
                    event.remove(db.engine, "before_cursor_execute", record)
                self.assertEqual((rows, total), ([], 0))
                self.assertTrue(any("count" in sql for sql in statements))
                self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))


if __name__ == "__main__":
    unittest.main()
