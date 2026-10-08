import unittest
from datetime import datetime

from flask import Flask, request
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.catalogos.controllers.categoria_utn_controller import CategoriaUtnController
from modules.catalogos.controllers.fuente_financiamiento_controller import FuenteFinanciamientoController
from modules.catalogos.models.categoria_utn import CategoriaUtn
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento


class CatalogosSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all(
            [CategoriaUtn(nombre=f"Categoria {i:02}") for i in range(12)]
            + [FuenteFinanciamiento(nombre=f"Fuente {i:02}") for i in range(12)]
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_catalogos_limitados_en_sql_y_contrato_http(self):
        for path, controller, table, prefix in (
            ("/categoria-utn/", CategoriaUtnController, "categoria_utn", "Categoria"),
            ("/fuente-financiamiento/", FuenteFinanciamientoController, "fuente_financiamiento", "Fuente"),
        ):
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _many):
                sql = statement.lower()
                if (f"from {table}" in sql or f"from (select {table}" in sql) and sql.lstrip().startswith("select"):
                    statements.append(sql)

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                with self.app.test_request_context(f"{path}?page=2&per_page=3"):
                    response, status = controller.listar(request)
            finally:
                event.remove(db.engine, "before_cursor_execute", record)

            body = response.get_json()
            self.assertEqual(status, 200)
            self.assertEqual([item["nombre"] for item in body["data"]],
                             [f"{prefix} {i:02}" for i in (3, 4, 5)])
            self.assertEqual(body["meta"]["total"], 12)
            self.assertEqual(body["meta"]["total_pages"], 4)
            self.assertEqual(body["meta"]["source"], "legacy-list")
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))
            self.assertFalse(any("limit" not in sql and "count" not in sql for sql in statements), statements)

    def test_modo_plano_y_pagina_vacia(self):
        with self.app.test_request_context("/categoria-utn/"):
            response, status = CategoriaUtnController.listar(request)
        self.assertEqual(status, 200)
        self.assertEqual(len(response.get_json()), 12)

        with self.app.test_request_context("/categoria-utn/?page=99&per_page=3"):
            response, status = CategoriaUtnController.listar(request)
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json()["data"], [])
        self.assertEqual(response.get_json()["meta"]["total"], 12)

    def test_parametros_invalidos(self):
        with self.app.test_request_context("/fuente-financiamiento/?page=0"):
            response, status = FuenteFinanciamientoController.listar(request)
        self.assertEqual(status, 400)
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_filtro_activos_y_orden_descendente(self):
        inactiva = CategoriaUtn.query.filter_by(nombre="Categoria 11").one()
        inactiva.deleted_at = datetime(2026, 1, 1)
        db.session.commit()

        with self.app.test_request_context("/categoria-utn/?page=1&per_page=3&orden=desc"):
            response, status = CategoriaUtnController.listar(request)
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json()["meta"]["total"], 11)
        self.assertEqual([item["nombre"] for item in response.get_json()["data"]],
                         ["Categoria 10", "Categoria 09", "Categoria 08"])

        with self.app.test_request_context("/categoria-utn/?page=1&per_page=3&activos=false"):
            response, status = CategoriaUtnController.listar(request)
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json()["meta"]["total"], 1)
        self.assertEqual(response.get_json()["data"][0]["nombre"], "Categoria 11")


if __name__ == "__main__":
    unittest.main()
