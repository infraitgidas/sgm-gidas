import unittest

from flask import Flask, g
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.proyectos.models.proyecto_investigacion import TipoProyecto
from modules.recursos.models.becas import Beca
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.search.services.search_service import SearchService
from modules.search.controllers.search_controller import SearchController


class SearchSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
                               SEARCH_MAX_PER_PAGE=9, SEARCH_MAX_QUERY_LENGTH=100,
                               SEARCH_MAX_SCAN_PER_MODEL=300)
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all(TipoProyecto(nombre=f"Proyecto Alpha {index:02}") for index in range(12))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_busqueda_limita_en_union_sql(self):
        statements = []

        def record(_conn, _cursor, sql, _params, _context, _many):
            statements.append(sql.lower())

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            data, total = SearchService.search_page("alpha", page=2, per_page=3)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(total, 12)
        self.assertEqual([item["titulo"] for item in data], [f"Proyecto Alpha {i:02}" for i in (3, 4, 5)])
        union_queries = [sql for sql in statements if "union all" in sql]
        self.assertTrue(any("count" in sql for sql in union_queries))
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in union_queries))
        loaded_types = [sql for sql in statements if "from tipo_proyecto_investigacion" in sql
                        and "union all" not in sql]
        self.assertTrue(loaded_types)
        self.assertTrue(all(" in (" in sql for sql in loaded_types))

        with self.app.test_request_context("/search/?q=alpha&page=2&per_page=3"):
            response, status = SearchController.buscar()
        self.assertEqual(status, 200)
        self.assertEqual(response.get_json()["total_resultados"], 12)
        self.assertEqual(len(response.get_json()["resultados"]), 3)

    def test_busqueda_cuenta_mas_de_trescientas_coincidencias(self):
        db.session.add_all(TipoProyecto(nombre=f"Proyecto Alpha extra {index:03}") for index in range(305))
        db.session.commit()
        data, total = SearchService.search_page("alpha", page=102, per_page=3, max_scan_per_model=30)
        self.assertEqual(total, 317)
        self.assertEqual(len(data), 3)

    def test_busqueda_por_relacion_y_acento(self):
        fuente = FuenteFinanciamiento(nombre="Financiación Especial")
        db.session.add(fuente)
        db.session.flush()
        db.session.add(Beca(nombre_beca="Beca externa", fuente_financiamiento_id=fuente.id))
        db.session.commit()
        data, total = SearchService.search_page("financiacion", page=1, per_page=3)
        self.assertEqual(total, 2)
        self.assertEqual({item["tipo"] for item in data}, {"Fuente de Financiamiento", "Beca"})

    def test_orden_global_entre_entidades(self):
        db.session.add_all((
            FuenteFinanciamiento(nombre="Global A"),
            TipoProyecto(nombre="Global B"),
            FuenteFinanciamiento(nombre="Global C"),
        ))
        db.session.commit()
        first, total = SearchService.search_page("global", page=1, per_page=2, orden="alf_desc")
        second, _ = SearchService.search_page("global", page=2, per_page=2, orden="alf_desc")
        self.assertEqual(total, 3)
        self.assertEqual([item["titulo"] for item in first + second],
                         ["Global C", "Global B", "Global A"])

    def test_busqueda_respeta_uct_antes_de_contar(self):
        db.session.add_all(
            GrupoInvestigacionUtn(id=index, mail=f"g{index}@example.com",
                                   nombre_unidad_academica="UTN", objetivo_desarrollo="Objetivo",
                                   nombre_sigla_grupo=f"UCT {index}")
            for index in (1, 2)
        )
        db.session.add_all((
            Beca(nombre_beca="Beca Secreta Uno", grupo_utn_id=1),
            Beca(nombre_beca="Beca Secreta Dos", grupo_utn_id=2),
        ))
        db.session.commit()
        with self.app.test_request_context("/search/?q=secreta"):
            g.current_grupo_utn_id = 1
            data, total = SearchService.search_page("secreta", page=1, per_page=9)
        self.assertEqual(total, 1)
        self.assertEqual(data[0]["titulo"], "Beca Secreta Uno")


if __name__ == "__main__":
    unittest.main()
