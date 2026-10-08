import unittest
from datetime import date, datetime
from unittest.mock import patch

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService
from modules.produccion.models.actividad_docencia import GradoAcademico, InvestigadorActividadGrado
from modules.shared.models.auditoria_campo import AuditoriaCampo


class ActividadHistorialSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all(
            AuditoriaCampo(
                entidad="actividad_y_catedra_posgrado", registro_id=1, campo="curso",
                valor_anterior="A", valor_nuevo=f"B{index}",
                fecha_cambio=datetime(2026, 1, index + 1),
            ) for index in range(7)
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_pagina_union_de_auditoria_y_grados(self):
        statements = []

        def record(_conn, _cursor, sql, _params, _context, _many):
            if "union all" in sql.lower():
                statements.append(sql.lower())

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            with self.app.test_request_context("/historial?page=2&per_page=3"):
                with patch.object(ActividadDocenciaService, "_obtener_actividad", return_value=type("A", (), {"id": 1})()):
                    result = ActividadDocenciaService.get_historial(1)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(result["meta"]["total"], 7)
        self.assertEqual([item["valor_nuevo"] for item in result["data"]], ["B3", "B2", "B1"])
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))

    def test_cambio_de_grado_se_integra_sin_cargar_todo_el_historial(self):
        db.session.add_all((GradoAcademico(id=1, nombre="Inicial"), GradoAcademico(id=2, nombre="Nuevo")))
        db.session.add_all((
            InvestigadorActividadGrado(id=1, investigador_id=1, actividad_docencia_id=1,
                                       grado_academico_id=1, fecha_inicio=date(2026, 1, 2)),
            InvestigadorActividadGrado(id=2, investigador_id=1, actividad_docencia_id=1,
                                       grado_academico_id=2, fecha_inicio=date(2026, 1, 7)),
        ))
        db.session.commit()
        with self.app.test_request_context("/historial?page=1&per_page=3"):
            result = ActividadDocenciaService._historial_page(1)
        self.assertEqual(result["meta"]["total"], 8)
        self.assertEqual([item["campo"] for item in result["data"]],
                         ["curso", "grado_academico_id", "curso"])
        self.assertEqual(result["data"][1]["valor_anterior"]["nombre"], "Inicial")
        self.assertEqual(result["data"][1]["valor_nuevo"]["nombre"], "Nuevo")


if __name__ == "__main__":
    unittest.main()
