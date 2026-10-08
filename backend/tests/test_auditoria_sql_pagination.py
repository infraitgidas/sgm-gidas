import re
import unittest
from datetime import datetime

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.shared.exceptions import ValidationError
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.auditoria_service import AuditoriaService
from modules.produccion.models.documentacion_autores import DocumentacionBibliografica
from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService


class AuditoriaSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            AuditoriaCampo(entidad="entidad_prueba", registro_id=1, campo="nombre",
                           valor_nuevo={"valor": index})
            for index in range(7)
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_historial_pagina_tres_filas_en_sql(self):
        statements = []

        def record(_conn, _cursor, statement, _params, _context, _many):
            sql = statement.lower()
            if re.search(r"\bfrom auditoria_campo\b", sql):
                statements.append(sql)

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            with self.app.test_request_context("/historial?page=2"):
                result = AuditoriaService.obtener_historial_entidad("entidad_prueba", 1)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

        self.assertEqual([item["id"] for item in result["data"]], [4, 3, 2])
        self.assertEqual(result["meta"]["per_page"], 3)
        self.assertEqual(result["meta"]["total"], 7)
        self.assertEqual(result["meta"]["total_pages"], 3)
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))
        self.assertFalse(any("limit" not in sql and "count" not in sql for sql in statements))

    def test_historial_plano_y_parametros_invalidos(self):
        with self.app.test_request_context("/historial"):
            result = AuditoriaService.obtener_historial_entidad("entidad_prueba", 1)
        self.assertEqual(len(result), 7)

        with self.app.test_request_context("/historial?page=0"):
            with self.assertRaises(ValidationError):
                AuditoriaService.obtener_historial_entidad("entidad_prueba", 1)

    def test_documentacion_filtra_antes_de_contar_y_limitar(self):
        db.session.add(DocumentacionBibliografica(
            id=9, titulo="Manual", editorial="UTN", anio=2026, grupo_id=1,
        ))
        events = (
            ("titulo", "Nuevo", 1),
            ("autores", {"accion": "vincular"}, 2),
            ("autores", {"accion": "consultar"}, 3),
            ("editorial", "Otra", 4),
            ("fecha", "2026-01-01", 5),
        )
        db.session.add_all(AuditoriaCampo(
            entidad="documentacion_bibliografica", registro_id=9,
            campo=field, valor_nuevo=value, fecha_cambio=datetime(2026, 1, day),
        ) for field, value, day in events)
        db.session.commit()
        with self.app.test_request_context("/historial?page=2&per_page=2"):
            result = DocumentacionBibliograficaService.get_historial(9)
        self.assertEqual(result["meta"]["total"], 4)
        self.assertEqual([item["campo"] for item in result["data"]], ["autores", "titulo"])


if __name__ == "__main__":
    unittest.main()
