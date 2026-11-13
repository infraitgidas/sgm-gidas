from copy import copy
from datetime import date
from types import SimpleNamespace
import unittest

from openpyxl import load_workbook

from modules.memorias.services.exportacion_service_impl import ExportService
from modules.memorias.services.memoria_excel_template import render_memoria, meeting_category, publication_category
from modules.memorias.services.memoria_excel_detail import display


class MemoriaFormatoTest(unittest.TestCase):
    def test_clasificacion_explicita_negativa_y_textos_con_prefijo_de_fecha(self):
        self.assertEqual(meeting_category({"alcance": "nacional", "referato": False, "tipo_reunion_nombre": "Nacional con referato"}), "sin clasificar")
        self.assertEqual(publication_category({"referato": False, "tipo_revista_nombre": "Revista con referato"}), "sin clasificar")
        self.assertEqual(display("2026-01-01 - Título completo"), "2026-01-01 - Título completo")
    def render(self, context=None, mutate=None, **records):
        sources = {key: [] for key in (
            "investigadores", "personal", "becarios", "equipamiento", "documentacion",
            "proyectos", "distinciones", "participaciones", "visitas", "trabajos_reunion",
            "trabajos_revista", "articulos", "registros", "actividades", "transferencias", "erogaciones",
        )}
        sources.update(records, memoria=SimpleNamespace(periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31)),
                       version=SimpleNamespace(numero_version=3))
        context = context or {"grupo": {"nombre_sigla_grupo": "OTRO GRUPO", "nombre_unidad_academica": "UTN",
                             "mail": "grupo@utn.edu.ar", "objetivo_desarrollo": "Objetivo institucional"}}
        original = load_workbook(ExportService.MEMORIA_TEMPLATE_PATH)
        if mutate:
            mutate(original["Hoja1"])
        return load_workbook(render_memoria(original, sources, context, ExportService))

    @staticmethod
    def text(sheet):
        return "\n".join(str(cell.value) for row in sheet for cell in row if cell.value is not None)

    def test_plantilla_no_aporta_contenido_incluso_cuando_cambian_los_ejemplos(self):
        def contaminate(sheet):
            for address in ("A5", "A19", "A23", "A27", "A42", "A44", "A47", "B62", "A150", "A322"):
                sheet[address] = "EJEMPLO DEL LABORATORIO QUE NO DEBE SALIR"
        output = self.render(mutate=contaminate)
        text = self.text(output["Hoja1"])
        for forbidden in ("EJEMPLO DEL LABORATORIO", "Secretario Administrativo", "GIDAS"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("NO APLICA", text.upper())
        self.assertIn("OTRO GRUPO", text)
        self.assertIn("Objetivo institucional", text)
        self.assertIn("Versión 3", text)
        self.assertFalse(any(cell.comment for sheet in output for row in sheet for cell in row))

    def test_se_conserva_la_estructura_institucional_y_sus_estilos(self):
        original = load_workbook(ExportService.MEMORIA_TEMPLATE_PATH)["Hoja1"]
        output = self.render()["Hoja1"]
        for row in (3, 4, 59, 60, 70, 75, 124, 130, 135, 209, 224, 265, 274, 305, 306):
            self.assertEqual(original.cell(row, 1).value, output.cell(row, 1).value)
            self.assertEqual(copy(original.cell(row, 1).font), copy(output.cell(row, 1).font))
            self.assertEqual(copy(original.cell(row, 1).fill), copy(output.cell(row, 1).fill))
        for col in "ABCDEFGHIJ":
            self.assertEqual(original.column_dimensions[col].width, output.column_dimensions[col].width)
        self.assertEqual({key: dict(value) for key, value in original.column_dimensions.items()},
                         {key: dict(value) for key, value in output.column_dimensions.items()})
        self.assertEqual(original.page_margins, output.page_margins)
        self.assertEqual(output.page_setup.fitToWidth, 1)
        self.assertEqual(output.page_setup.fitToHeight, 0)
        self.assertTrue(output.print_area)

    def test_desbordes_conservan_registros_encabezados_y_bordes(self):
        output = self.render(
            investigadores=[{"nombre_apellido": f"Persona {i}"} for i in range(25)],
            personal=[{"nombre_apellido": f"Apoyo {i}", "tipo_personal_nombre": "Apoyo"} for i in range(10)],
            becarios=([{"nombre_apellido": f"Doctorando {i}", "tipo_formacion_nombre": "Doctorado"} for i in range(9)] +
                      [{"nombre_apellido": f"Tesista {i}", "tipo_formacion_nombre": "Tesina"} for i in range(5)]),
            equipamiento=[{"denominacion": f"Equipo {i}"} for i in range(11)],
            proyectos=[{"codigo_proyecto": f"PID-{i}"} for i in range(10)],
        )["Hoja1"]
        values = [cell.value for row in output for cell in row]
        for prefix, count in (("Persona ", 25), ("Apoyo ", 10), ("Doctorando ", 9), ("Tesista ", 5), ("Equipo ", 11), ("PID-", 10)):
            for i in range(count):
                self.assertIn(f"{prefix}{i}", values)
        original = load_workbook(ExportService.MEMORIA_TEMPLATE_PATH)["Hoja1"]
        self.assertIn(original["A305"].value, values)
        self.assertIn("VI - PROGRAMA", self.text(output))
        for row in output:
            cell = row[1]
            if isinstance(cell.value, str) and cell.value.startswith(("Apoyo ", "Tesista ")):
                self.assertTrue(cell.border.left.style)
                self.assertTrue(cell.border.bottom.style)
                self.assertTrue(cell.alignment.wrap_text)
            if isinstance(row[2].value, str) and row[2].value.startswith("PID-"):
                self.assertTrue(row[1].border.bottom.style)
                self.assertTrue(row[1].border.top.style)

    def test_libros_no_se_duplican_y_desconocidos_no_se_inventan(self):
        output = self.render(
            trabajos_revista=[
                {"titulo_trabajo": "REVISTA VERIFICADA", "tipo_revista_nombre": "Revista con referato"},
                {"titulo_trabajo": "LIBRO ÚNICO", "tipo_revista_nombre": "Libro o capítulo de libro", "issn": "ISBN 1"},
                {"titulo_trabajo": "REVISTA SIN CLASIFICAR", "tipo_revista_nombre": "Nacional"}],
            trabajos_reunion=[
                {"titulo_trabajo": "CONGRESO DESCONOCIDO", "tipo_reunion_nombre": "Congreso"},
                {"titulo_trabajo": "NACIONAL VERIFICADO", "tipo_reunion_nombre": "Nacional con referato"},
                {"titulo_trabajo": "INTERNACIONAL VERIFICADO", "tipo_reunion_nombre": "Internacional con referato"}],
            becarios=[{"nombre_apellido": "FORMACIÓN DESCONOCIDA", "tipo_formacion_nombre": "Lic"}],
            transferencias=[{"denominacion": "CONTRATO DESCONOCIDO", "tipo_contrato_nombre": "Convenio TEST"}],
            registros=[{"nombre_articulo": "REGISTRO DESCONOCIDO", "tipo_registro_nombre": "Otro"}],
        )
        main, detail = self.text(output["Hoja1"]), self.text(output["Detalle académico"])
        self.assertEqual(main.count("LIBRO ÚNICO"), 1)
        for value in ("REVISTA VERIFICADA", "NACIONAL VERIFICADO", "INTERNACIONAL VERIFICADO"):
            self.assertIn(value, main)
        for value in ("CONGRESO DESCONOCIDO", "REVISTA SIN CLASIFICAR", "FORMACIÓN DESCONOCIDA", "CONTRATO DESCONOCIDO", "REGISTRO DESCONOCIDO"):
            self.assertNotIn(value, main)
            self.assertIn(value, detail)
        self.assertIn("sin clasificar", detail)

    def test_contenido_completo_fechas_nativas_y_detalle_financiero(self):
        output = self.render(
            articulos=[{"titulo": "Título de divulgación", "descripcion": "Resultados completos", "fecha_publicacion": "2026-06-02"}],
            participaciones=[{"nombre_evento": "Curso abierto", "forma_participacion": "Ponente", "fecha": "2026-03-04", "investigador_nombre": "Persona participante"}],
            visitas=[{"razon": "Cooperación", "procedencia": "Universidad", "fecha": "2026-04-05", "tipo_visita_nombre": "Académica"}],
            actividades=[{"curso": "Materia", "institucion": "Universidad", "rol_actividad_nombre": "Titular", "fecha_inicio": "2026-02-01"}],
            proyectos=[{"codigo_proyecto": "PID", "monto_destinado": "1234.56"}],
            erogaciones=[{"numero_movimiento": 57, "tipo_movimiento": "INGRESO", "monto": "100", "moneda": "USD", "monto_equivalente_ars": "2000", "fecha": "2026-01-01"}],
        )
        for value in ("Título de divulgación", "Resultados completos", "Persona participante", "04/03/2026", "Académica", "Titular"):
            self.assertIn(value, self.text(output["Hoja1"]))
        detail = output["Detalle académico"]
        self.assertIn(1234.56, [cell.value for row in detail for cell in row])
        self.assertIn(57, [cell.value for row in detail for cell in row])
        date_cell = next(cell for row in detail for cell in row if str(cell.value).startswith("2026-01-01"))
        self.assertTrue(date_cell.is_date)
        self.assertEqual(date_cell.number_format, "dd/mm/yyyy")
        main = output["Hoja1"]
        heading = next(cell.row for row in main for cell in row if cell.value == "Erogaciones Corrientes")
        self.assertEqual(main.cell(heading + 2, 3).value, 2000)

    def test_no_sumar_dolares_como_pesos_si_falta_conversion(self):
        output = self.render(erogaciones=[
            {"numero_movimiento": 1, "tipo_movimiento": "INGRESO", "monto": 100, "moneda": "USD"},
            {"numero_movimiento": 2, "tipo_movimiento": "INGRESO", "monto": 500, "moneda": "ARS"},
        ])
        self.assertEqual(output["Hoja1"]["C309"].value, 500)
        self.assertIn("Movimiento sin equivalencia ARS: 1", self.text(output["Detalle académico"]))

    def test_movimientos_sin_tipo_o_categoria_no_se_convierten_en_egresos(self):
        output = self.render(erogaciones=[
            {"numero_movimiento": 1, "tipo_movimiento": "OTRO", "categoria_erogacion_codigo": "CORRIENTE", "monto": 100},
            {"numero_movimiento": 2, "tipo_movimiento": "EGRESO", "monto": 300},
        ])
        self.assertIn("Revisar movimientos excluidos", self.text(output["Hoja1"]))
        self.assertIn("Movimiento sin clasificación contable: 1", self.text(output["Detalle académico"]))
        self.assertIn("Movimiento sin clasificación contable: 2", self.text(output["Detalle académico"]))

    def test_importes_originales_con_moneda_y_fechas_en_formulario(self):
        sheet = self.render(equipamiento=[
            {"denominacion": "Equipo USD", "monto_invertido": "123.45", "moneda": "USD", "fecha_incorporacion": "2026-01-02"},
            {"denominacion": "Monto desconocido"},
        ])["Hoja1"]
        self.assertEqual(sheet["D126"].value, 123.45)
        self.assertEqual(sheet["D126"].number_format, '"USD" #,##0.00')
        self.assertIsNone(sheet["D127"].value)
        self.assertTrue(sheet["C126"].is_date)
        self.assertEqual(sheet["C126"].number_format, "dd/mm/yyyy")

    def test_autoridades_al_cierre_y_todas_las_vigencias_en_detalle(self):
        context = {"grupo": {"nombre_sigla_grupo": "GRUPO", "nombre_unidad_academica": "UTN", "mail": "mail", "objetivo_desarrollo": "Objetivo"},
                   "directivos": [{"cargo": "Director", "nombre_apellido": "Director anterior", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-06-30"},
                                  {"cargo": "Director", "nombre_apellido": "Director al cierre", "fecha_inicio": "2026-07-01", "fecha_fin": None}]}
        output = self.render(context=context)
        self.assertIn("Director al cierre", output["Hoja1"]["A7"].value)
        self.assertNotIn("Director anterior", output["Hoja1"]["A7"].value)
        detail = self.text(output["Detalle académico"])
        self.assertIn("Director anterior", detail)
        self.assertIn("2026-06-30", detail)

    def test_textos_extremos_no_se_recortan_ni_exceden_limites_de_excel(self):
        long_text = "Resultado científico. " * 1800
        output = self.render(articulos=[{"titulo": "Texto largo", "descripcion": long_text}])
        for sheet in output:
            self.assertTrue(all((dimension.height or 15) <= 409 for dimension in sheet.row_dimensions.values()))
            self.assertTrue(all(len(cell.value) <= 32767 for row in sheet for cell in row if isinstance(cell.value, str)))
        detail_values = [cell.value for row in output["Detalle académico"] for cell in row
                         if cell.column == 2 and isinstance(cell.value, str) and "Resultado" in cell.value]
        self.assertEqual("".join(detail_values), long_text)
        article_cells = [cell for row in output["Hoja1"] for cell in row if isinstance(cell.value, str) and "Resultado científico" in cell.value]
        self.assertGreater(len(article_cells), 1)

    def test_formulas_de_texto_no_se_ejecutan_ni_se_filtran_ids_de_auditoria(self):
        output = self.render(articulos=[{"titulo": "=HYPERLINK(\"evil\")", "descripcion": "=1+1", "created_by_nombre": "AUDITOR PRIVADO"}])
        values = [cell.value for sheet in output for row in sheet for cell in row]
        self.assertIn("=1+1", values)
        self.assertNotIn("AUDITOR PRIVADO", values)
        self.assertFalse(any(cell.data_type == "f" for sheet in output for row in sheet for cell in row))


if __name__ == "__main__":
    unittest.main()
