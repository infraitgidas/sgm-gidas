import unittest

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.produccion.models.documentacion_autores import Autor
from modules.produccion.models.actividad_docencia import GradoAcademico, RolActividad
from modules.produccion.models.registro_patente import TipoRegistroPropiedad
from modules.produccion.models.trabajo_reunion import TipoReunion
from modules.produccion.models.trabajo_revista import TipoRevista
from modules.proyectos.models.proyecto_investigacion import TipoProyecto
from modules.produccion.services.autores_service import AutorService
from modules.produccion.services.grado_academico_service import GradoAcademicoService
from modules.produccion.services.rol_actividad_service import RolActividadService
from modules.produccion.services.tipo_registro_service import TipoRegistroPropiedadService
from modules.produccion.services.tipo_reunion_service import TipoReunionService
from modules.produccion.services.tipo_revista_service import TipoRevistaService
from modules.proyectos.services.tipo_proyecto_service import TipoProyectoService
from modules.produccion.controllers.autores_controller import AutorController
from modules.proyectos.controllers.tipo_proyecto_controller import TipoProyectoController


CASES = (
    (Autor, AutorService, "nombre_apellido"),
    (GradoAcademico, GradoAcademicoService, "nombre"),
    (RolActividad, RolActividadService, "nombre"),
    (TipoRegistroPropiedad, TipoRegistroPropiedadService, "nombre"),
    (TipoReunion, TipoReunionService, "nombre"),
    (TipoRevista, TipoRevistaService, "nombre"),
    (TipoProyecto, TipoProyectoService, "nombre"),
)


class ProduccionCatalogSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        for model, _, field in CASES:
            db.session.add_all(model(**{field: f"Nombre {index:02}"}) for index in range(12))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_consulta_limitada_y_orden_estable(self):
        for model, service, field in CASES:
            with self.subTest(model=model.__name__):
                statements = []

                def record(_conn, _cursor, statement, _params, _context, _many):
                    if statement.lstrip().lower().startswith("select"):
                        statements.append(statement.lower())

                event.listen(db.engine, "before_cursor_execute", record)
                try:
                    rows, total = service.get_page(2, 3, orden="desc")
                finally:
                    event.remove(db.engine, "before_cursor_execute", record)
                self.assertEqual(total, 12)
                self.assertEqual([row[field] for row in rows], [f"Nombre {i:02}" for i in (8, 7, 6)])
                self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))

    def test_contrato_http_y_validacion(self):
        with self.app.test_request_context("/autores?page=2&per_page=3"):
            response, status = AutorController.get_all()
            self.assertEqual(status, 200)
            self.assertEqual(response.get_json()["meta"]["total"], 12)
            self.assertEqual(len(response.get_json()["data"]), 3)
        with self.app.test_request_context("/tipos-proyecto"):
            response, status = TipoProyectoController.get_all()
            self.assertEqual(status, 200)
            self.assertEqual(len(response.get_json()), 12)
        with self.app.test_request_context("/tipos-proyecto?page=0"):
            response, status = TipoProyectoController.get_all()
            self.assertEqual(status, 400)
            self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
