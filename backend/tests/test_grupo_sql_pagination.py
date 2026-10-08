import re
import unittest
from datetime import date

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.grupo.models.programa_actividades import PlanificacionGrupo
from modules.grupo.models.programa_incentivos import ProgramaIncentivos
from modules.grupo.models.visita_grupo import TipoVisita, VisitaAcademica
from modules.grupo.services.programa_actividades_service import listar_planificaciones_paginado
from modules.grupo.services.programa_incentivos_service import listar_programas_incentivos_paginado
from modules.grupo.services.tipo_visita_service import TipoVisitaService
from modules.grupo.services.visita_service import listar_visitas_paginado


class GrupoSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add(GrupoInvestigacionUtn(
            id=1, mail="uct@example.test", nombre_unidad_academica="Regional",
            objetivo_desarrollo="Investigacion", nombre_sigla_grupo="UCT",
        ))
        db.session.add(TipoVisita(id=1, nombre="Tipo 01"))
        db.session.flush()
        for index in range(1, 13):
            db.session.add_all([
                ProgramaIncentivos(nombre=f"Programa {index:02}"),
                PlanificacionGrupo(descripcion=f"Plan {index:02}", anio=2025,
                                    grupo_id=1),
            ])
            if index > 1:
                db.session.add(TipoVisita(nombre=f"Tipo {index:02}"))
            db.session.add(VisitaAcademica(
                razon=f"Visita {index:02}", fecha=date(2025, 1, 1),
                procedencia="Regional", tipo_visita_id=1, grupo_utn_id=1,
            ))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_listados_de_grupo_limitados_en_sql(self):
        for table, service in (
            ("programa_incentivos_investigador", listar_programas_incentivos_paginado),
            ("tipo_visita", TipoVisitaService.get_page),
            ("planificacion_grupo", listar_planificaciones_paginado),
            ("visita_grupo", listar_visitas_paginado),
        ):
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _many):
                sql = statement.lower()
                if re.search(rf"\bfrom {table}\b", sql):
                    statements.append(sql)

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                rows, total = service(2, 3)
            finally:
                event.remove(db.engine, "before_cursor_execute", record)

            self.assertEqual((len(rows), total), (3, 12))
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements), table)
            self.assertFalse(any("limit" not in sql and "count" not in sql for sql in statements), table)


if __name__ == "__main__":
    unittest.main()
