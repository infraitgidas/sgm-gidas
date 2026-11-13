"""Completa la plantilla institucional sin reconstruir su maquetación."""
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass
from io import BytesIO
from math import ceil
from textwrap import wrap
import unicodedata

from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange

from modules.memorias.services.memoria_excel_detail import (
    MISSING, civil_date, describe, write_academic_detail,
)

EMPTY = "No registra datos en este período."
# Sólo títulos, instrucciones y nombres de columnas. Nunca ejemplos ni valores.
STRUCTURE_ROWS = {
    3, 4, 11, 17, 45, 59, 60, 61, 70, 71, 75, 76, 78, 79, 80, 84, 85,
    91, 92, 96, 97, 106, 107, 118, 119, 124, 125, 130, 131, 135, 136,
    137, 138, 143, 146, 149, 191, 196, 205, 209, 210, 211, 219, 220,
    224, 225, 226, 232, 238, 250, 256, 257, 261, 265, 266, 274, 275,
    276, 277, 282, 283, 287, 288, 291, 292, 296, 297, 300, 301,
    305, 306, 307, 308, 316, 317,
}


@dataclass(frozen=True)
class ImporteOriginal:
    valor: Decimal
    moneda: str


def importe_original(item, campo):
    value = item.get(campo)
    return ImporteOriginal(Decimal(str(value)), item.get("moneda") or "ARS") if value is not None else None


class TemplateWriter:
    def __init__(self, workbook):
        self.workbook = workbook
        self.sheet = workbook["Hoja1"]
        self.source = workbook.copy_worksheet(self.sheet)
        self.insertions = []
        self.required_heights = {}
        self.warnings = []
        for row in self.sheet:
            for cell in row:
                if not isinstance(cell, MergedCell):
                    cell.comment = None
                    cell.hyperlink = None
                    if cell.row not in STRUCTURE_ROWS:
                        cell.value = None

    def row(self, original):
        return original + sum(amount for position, amount in self.insertions if position <= original)

    def clear(self, start, end):
        for cells in self.sheet.iter_rows(min_row=self.row(start), max_row=self.row(end), max_col=12):
            for cell in cells:
                if not isinstance(cell, MergedCell):
                    cell.value = None
                    cell.comment = None

    def set(self, original_row, column, value, *, content=True):
        return self.set_at(self.row(original_row), column, value, content=content)

    def set_at(self, row, column, value, *, content=True):
        cell = self.sheet[f"{column}{row}"]
        importe = value if isinstance(value, ImporteOriginal) else None
        if importe is not None:
            value = importe.valor
        style = copy(cell._style)
        if isinstance(value, str) and len(value) > 32767:
            value = value[:280] + "\nTexto completo en Detalle académico (excede la capacidad de una celda de Excel)."
        cell.value = value
        cell._style = style
        if importe is not None:
            cell.number_format = f'"{importe.moneda}" #,##0.00'
        elif isinstance(value, (date, datetime)):
            cell.number_format = "dd/mm/yyyy"
        if isinstance(value, str):
            cell.data_type = "s"
        if value is not None:
            font = copy(cell.font)
            font.color = "FF000000"
            font.vertAlign = None
            if content:
                # Algunos ejemplos del laboratorio contienen formato de edición
                # (subrayados y tamaños grandes), no una jerarquía académica.
                font.sz = min(12, max(10, font.sz or 11))
                font.u = None
            cell.font = font
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            alignment.vertical = "top"
            if content:
                alignment.textRotation = 0
                alignment.shrinkToFit = False
                if isinstance(value, str) and (len(value) > 100 or "\n" in value):
                    alignment.horizontal = "left"
            cell.alignment = alignment
            self.fit_text(cell)
        return cell

    def fit_text(self, cell):
        if not isinstance(cell.value, str) or not cell.alignment.wrap_text:
            return
        merged = next((item for item in self.sheet.merged_cells.ranges if cell.coordinate in item), None)
        first, last = (merged.min_col, merged.max_col) if merged else (cell.column, cell.column)
        width = sum(self.column_width(column) for column in range(first, last + 1))
        lines = sum(max(1, len(wrap(line, width=max(10, int(width * 0.85))))) for line in cell.value.split("\n"))
        needed = ceil(lines * max(15, (cell.font.sz or 11) * 1.5) + 6)
        final_row = merged.max_row if merged else cell.row
        heights = [self.sheet.row_dimensions[row].height or self.sheet.sheet_format.defaultRowHeight or 15
                   for row in range(cell.row, final_row + 1)]
        if needed > sum(heights):
            required = heights[0] + needed - sum(heights)
            self.required_heights[cell.row] = max(self.required_heights.get(cell.row, 0), required)
            self.sheet.row_dimensions[cell.row].height = min(409, required)

    def column_width(self, column):
        # K y L no tienen dimensión explícita. Consultar una columna ausente
        # por [] crea una dimensión de 13 y altera el formato exportado.
        dimension = self.sheet.column_dimensions.get(get_column_letter(column))
        if dimension is None:
            dimension = next((item for item in self.sheet.column_dimensions.values()
                              if item.min <= column <= item.max), None)
        return dimension.width if dimension and dimension.width else self.sheet.sheet_format.defaultColWidth or 13

    def insert(self, before, amount, prototype):
        if not amount:
            return
        at = self.row(before)
        ranges = []
        for merged in self.sheet.merged_cells.ranges:
            updated = CellRange(str(merged))
            if updated.min_row >= at:
                updated.shift(row_shift=amount)
            elif updated.max_row >= at:
                updated.max_row += amount
            ranges.append(str(updated))
        dimensions = {index: copy(dimension) for index, dimension in self.sheet.row_dimensions.items()}
        self.sheet.insert_rows(at, amount)
        self.sheet.row_dimensions.clear()
        self.required_heights = {row + amount if row >= at else row: height for row, height in self.required_heights.items()}
        for index, dimension in dimensions.items():
            new_index = index + amount if index >= at else index
            dimension.index = new_index
            self.sheet.row_dimensions[new_index] = dimension
        self.sheet.merged_cells = MultiCellRange()
        for merged in ranges:
            self.sheet.merge_cells(merged)
        for target in range(at, at + amount):
            self.clone_row(prototype, target)
        for page_break in self.sheet.row_breaks.brk:
            if page_break.id >= at:
                page_break.id += amount
        self.insertions.append((before, amount))

    def clone_row(self, prototype, target):
        dimension = copy(self.source.row_dimensions[prototype])
        dimension.index = target
        self.sheet.row_dimensions[target] = dimension
        for column in range(1, 13):
            self.sheet.cell(target, column)._style = copy(self.source.cell(prototype, column)._style)
        for merged in self.source.merged_cells.ranges:
            if merged.min_row == prototype and merged.max_row == prototype:
                self.sheet.merge_cells(start_row=target, end_row=target,
                    start_column=merged.min_col, end_column=merged.max_col)

    def record_layout(self, row, columns, prototype, replace_placeholder=False):
        for merged in list(self.sheet.merged_cells.ranges):
            if merged.min_row <= row <= merged.max_row:
                self.sheet.unmerge_cells(str(merged))
        for column in range(1, 13):
            self.sheet.cell(row, column).value = None
        self.clone_row(prototype, row)
        self.sheet.row_dimensions[row].height = 24
        # Varios prototipos tienen lados faltantes. Completar el delineado sin
        # cambiar el grosor/color de los lados que sí define el laboratorio.
        for column in columns:
            cell = self.sheet[f"{column}{row}"]
            border = copy(cell.border)
            for edge in ("left", "right", "top", "bottom"):
                side = getattr(border, edge)
                if side is None or not side.style:
                    setattr(border, edge, Side(style="thin", color="FF000000"))
            cell.border = border

    def table(self, start, end, columns, records, *, prototype=None, empty_row=None, replace_placeholder=False):
        records = list(records)
        prototype = prototype or start
        self.clear(start, end)
        self.insert(end + 1, max(0, len(records) - (end - start + 1)), prototype)
        if not records:
            first, last = self.row(start), self.row(end)
            for merged in list(self.sheet.merged_cells.ranges):
                if first <= merged.min_row <= last:
                    self.sheet.unmerge_cells(str(merged))
            end_col = max(self.source[f"{column}{start - 1}"].column for column in columns)
            for merged in self.source.merged_cells.ranges:
                if merged.min_row == start - 1 and merged.min_col <= end_col:
                    end_col = max(end_col, merged.max_col)
            self.sheet.merge_cells(start_row=first, end_row=first, start_column=1, end_column=end_col)
            for row in range(first, last + 1):
                self.sheet.row_dimensions[row].height = 24 if row == first else 6
                self.sheet.row_dimensions[row].hidden = row != first
            self.set_at(first, "A", "Sin registros para esta sección. Consulte el detalle académico.")
            return
        first = self.row(start)
        for index, values in enumerate(records):
            row = first + index
            self.record_layout(row, columns, prototype, replace_placeholder)
            for column, value in zip(columns, values):
                self.set_at(row, column, value)
        for row in range(first + len(records), self.row(end) + 1):
            self.sheet.row_dimensions[row].height = 6
            self.sheet.row_dimensions[row].hidden = True

    def narrative(self, start, end, paragraphs, *, empty_row=None):
        paragraphs = [str(value) for value in paragraphs if value not in (None, "")]
        paragraphs = [chunk for paragraph in paragraphs for chunk in
                      (wrap(paragraph, 6000, replace_whitespace=False, drop_whitespace=False, expand_tabs=False)
                       if len(paragraph) > 6000 else [paragraph])]
        # No se decide la distribución leyendo los ejemplos del laboratorio.
        paragraphs = paragraphs or [EMPTY]
        self.insert(end + 1, max(0, len(paragraphs) - (end - start + 1)), 144)
        first, last = self.row(start), self.row(end)
        for merged in list(self.sheet.merged_cells.ranges):
            if first <= merged.min_row <= last:
                self.sheet.unmerge_cells(str(merged))
        self.clear(start, end)
        for row in range(first, last + 1):
            self.sheet.row_dimensions[row].height = 6
            self.sheet.row_dimensions[row].hidden = True
        for index, paragraph in enumerate(paragraphs):
            target = first + index
            self.sheet.merge_cells(start_row=target, end_row=target, start_column=1, end_column=6)
            self.sheet.cell(target, 1)._style = copy(self.source["A144"]._style)
            self.sheet.row_dimensions[target].height = 24
            self.sheet.row_dimensions[target].hidden = False
            self.set_at(target, "A", paragraph)

    def finish(self):
        self.expand_tall_rows()
        self.workbook.remove(self.source)
        for sheet in list(self.workbook):
            if sheet != self.sheet and sheet.title != "Detalle académico":
                self.workbook.remove(sheet)
        self.sheet.print_area = f"A1:L{self.sheet.max_row}"
        self.sheet.sheet_properties.pageSetUpPr.fitToPage = True
        self.sheet.page_setup.fitToWidth = 1
        self.sheet.page_setup.fitToHeight = 0
        self.workbook.properties.title = "Memoria académica"
        self.workbook.properties.creator = "GIDAS"
        self.workbook.properties.lastModifiedBy = "GIDAS"
        self.workbook.properties.description = None
        output = BytesIO()
        self.workbook.save(output)
        output.seek(0)
        return output

    def expand_tall_rows(self):
        """Excel limita cada fila a 409 puntos: distribuir sin recortar texto."""
        for row, height in sorted(self.required_heights.items(), reverse=True):
            if height <= 409:
                continue
            count = ceil(height / 400)
            amount = count - 1
            at = row + 1
            ranges = [CellRange(str(item)) for item in self.sheet.merged_cells.ranges]
            horizontal = {item.min_col: item.max_col for item in ranges
                          if item.min_row == row and item.max_row == row}
            occupied = {col for first, last in horizontal.items() for col in range(first + 1, last + 1)}
            values = [(cell.column, copy(cell._style)) for cell in self.sheet[row] if not isinstance(cell, MergedCell)]
            for item in list(self.sheet.merged_cells.ranges):
                self.sheet.unmerge_cells(str(item))
            dimensions = {index: copy(dim) for index, dim in self.sheet.row_dimensions.items()}
            self.sheet.insert_rows(at, amount)
            self.sheet.row_dimensions.clear()
            for index, dim in dimensions.items():
                dim.index = index + amount if index >= at else index
                self.sheet.row_dimensions[dim.index] = dim
            for item in ranges:
                if item.min_row >= at:
                    item.shift(row_shift=amount)
                elif item.max_row >= row:
                    item.max_row += amount
                self.sheet.merge_cells(str(item))
            for column, style in values:
                if column in occupied:
                    continue
                if column not in horizontal:
                    self.sheet.merge_cells(start_row=row, end_row=row + amount,
                                           start_column=column, end_column=column)
                self.sheet.cell(row, column)._style = style
            for index in range(row, row + count):
                self.sheet.row_dimensions[index].height = ceil(height / count)
            for page_break in self.sheet.row_breaks.brk:
                if page_break.id >= at:
                    page_break.id += amount


def money(item):
    value = item.get("monto_equivalente_ars")
    if value is None and (item.get("moneda") or "ARS") == "ARS":
        value = item.get("monto")
    return Decimal(str(value)) if value is not None else None


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c)).casefold()


def publication_category(item):
    kind = normalized(item.get("tipo_revista_nombre"))
    if "libro" in kind or "isbn" in normalized(item.get("issn")):
        return "libro"
    if item.get("referato") is True or (item.get("referato") is None and "con referato" in kind):
        return "revista"
    return "sin clasificar"


def meeting_category(item):
    kind = normalized(item.get("tipo_reunion_nombre"))
    scope = item.get("alcance")
    if scope == "internacional" or (scope is None and "internacional" in kind):
        return "internacional"
    national = scope == "nacional" or (scope is None and "nacional" in kind)
    reviewed = item.get("referato") is True or (item.get("referato") is None and "con referato" in kind)
    return "nacional" if national and reviewed else "sin clasificar"


def transfer_category(item):
    kind = normalized(item.get("tipo_contrato_nombre"))
    for token, category in (("tecnolog", "tecnologia"), ("i+d", "idi"), ("idi", "idi"),
                            ("conocimiento", "conocimientos"), ("asistencia", "asistencia"), ("consultoria", "asistencia"),
                            ("servicio", "servicios"), ("ensayo", "servicios"), ("difusion", "difusion")):
        if token in kind:
            return category
    return "sin clasificar"


def personal_category(item):
    kind = normalized(item.get("tipo_personal_nombre"))
    if "profesional" in kind:
        return "profesional"
    if "apoyo" in kind or "tecnico" in kind or "administrativ" in kind:
        return "apoyo"
    return "sin clasificar"


def fellow_category(item, helpers):
    kind = normalized(item.get("tipo_formacion_nombre"))
    tokens = ("doctor", "maestr", "especial", "graduad", "pasant", "tesina", "tesis", "proyecto final", "trabajo final", "alumno", "estudiante")
    return helpers._clasificar_becario(kind) if any(token in kind for token in tokens) else "sin clasificar"


def property_category(item):
    kind = normalized(item.get("tipo_registro_nombre"))
    for token in ("patente", "industrial", "intelectual"):
        if token in kind:
            return token
    return "sin clasificar"



def render_memoria(workbook, sources, context, helpers):
    w = TemplateWriter(workbook)
    group = context["grupo"]
    memoria = sources["memoria"]
    year = memoria.periodo_fin.year
    sigla = group["nombre_sigla_grupo"].rsplit(" - ", 1)[-1]
    label = str(year) if memoria.periodo_inicio == date(year, 1, 1) and memoria.periodo_fin == date(year, 12, 31) else f"{helpers._format_date(memoria.periodo_inicio)} al {helpers._format_date(memoria.periodo_fin)}"
    w.set(1, "A", f"MEMORIAS {label} DEL GRUPO UTN - {sigla}", content=False)
    directivos = context.get("directivos", [])

    def authority(cargo):
        matching = [item for item in directivos if (item.get("cargo") or "").strip().casefold() == cargo.casefold()]
        matching.sort(key=lambda item: item.get("fecha_inicio") or "")
        end = memoria.periodo_fin.isoformat()
        matching = [item for item in matching if (item.get("fecha_inicio") or "") <= end
                    and (not item.get("fecha_fin") or item["fecha_fin"] >= end)]
        return matching[-1]["nombre_apellido"] if matching else MISSING

    prefixes = {5: "1.1.- Facultad Regional", 6: "1.2.- Nombre y Sigla", 7: "1.3.- Director",
                8: "1.4.- Vicedirector", 9: "1.5.- Dirección de Email"}
    for row, value in ((5, group["nombre_unidad_academica"]), (6, group["nombre_sigla_grupo"]), (7, authority("Director")),
                       (8, authority("Vicedirector")), (9, group["mail"])):
        prefix = prefixes[row]
        w.set(row, "A", f"{prefix}: {value}", content=False)
    consejo = [item for item in directivos if "consejo" in (item.get("cargo") or "").casefold()]
    w.set(10, "A", "1.6.- Integrantes del Consejo Ejecutivo", content=False)
    w.table(12, 15, ["A", "B", "D"], [[i, item["nombre_apellido"], item.get("cargo") or "-"] for i, item in enumerate(consejo, 1)])
    w.set(19, "A", "Autoridades al cierre del período", content=False)
    w.set(21, "A", "Director: " + authority("Director"))
    w.set(22, "A", "Vicedirector: " + authority("Vicedirector"))
    w.narrative(23, 44, ["Estructura científica, tecnológica y administrativa: " + MISSING,
                             "Disciplinas prioritarias y campos de aplicación: " + MISSING])
    version = sources.get("version")
    w.sheet.merge_cells("A2:F2")
    w.set(2, "A", f"Versión {getattr(version, 'numero_version', 'sin informar')} · "
          "Autoridades históricas, información complementaria y registros sin clasificar en Detalle académico.")
    w.sheet["A2"].hyperlink = "#'Detalle académico'!A1"
    w.narrative(47, 56, [group.get("objetivo_desarrollo")])
    w.table(62, 67, ["A", "B", "C", "D", "E", "F"], [[i, item.get("nombre_apellido"), item.get("categoria_utn_nombre") or "-",
        item.get("programa_incentivos_nombre") or "-", item.get("tipo_dedicacion_nombre") or "-", item.get("horas_semanales")]
        for i, item in enumerate(sources["investigadores"], 1)])
    for start, end, category in ((72, 73, "profesional"), (77, 77, "apoyo")):
        items = [item for item in sources["personal"] if personal_category(item) == category]
        w.table(start, end, ["A", "B", "C"], [[i, item.get("nombre_apellido"), item.get("horas_semanales")] for i, item in enumerate(items, 1)], prototype=72)
    for start, end, category in ((81, 83, "doctorado"), (86, 89, "maestria"), (93, 94, "graduado"),
                                  (98, 104, "alumno"), (108, 116, "pasante"), (120, 122, "tesina")):
        items = [item for item in sources["becarios"] if fellow_category(item, helpers) == category]
        w.table(start, end, ["A", "B", "C", "D"], [[i, item.get("nombre_apellido"), item.get("fuentes_financiamiento_beca") or "-", item.get("horas_semanales")]
            for i, item in enumerate(items, 1)], prototype=86,
            empty_row=82 if category == "doctorado" else None, replace_placeholder=category == "doctorado")
    w.set(84, "A", "Maestría/Especialización", content=False)
    w.table(126, 128, ["A", "B", "C", "D", "E"], [[i, item.get("denominacion"), civil_date(item.get("fecha_incorporacion")),
        importe_original(item, "monto_invertido"), item.get("descripcion_breve")] for i, item in enumerate(sources["equipamiento"], 1)])
    w.table(132, 133, ["A", "B", "C", "D", "E", "F"], [[i, item.get("titulo"), helpers._join_dict_names(item.get("autores"), "nombre_apellido"),
        item.get("editorial"), item.get("anio"), civil_date(item.get("fecha"))] for i, item in enumerate(sources["documentacion"], 1)])
    w.set(131, "F", "Fecha", content=False)
    w.set(137, "A", "Proyectos del período", content=False)
    w.table(139, 141, ["A", "B", "C", "D", "F", "G", "H", "I", "J"], [[i, item.get("tipo_proyecto_nombre"), item.get("codigo_proyecto"),
        helpers._format_period(civil_date(item.get("fecha_inicio")), civil_date(item.get("fecha_fin"))), item.get("nombre_proyecto"),
        item.get("descripcion_proyecto"), item.get("logros_obtenidos") or context.get("logros_proyectos", {}).get(str(item.get("proyecto_investigacion_id")), MISSING),
        item.get("dificultades_proyecto") or "-", item.get("fuente_financiamiento_nombre") or "-"] for i, item in enumerate(sources["proyectos"], 1)])
    w.narrative(144, 145, [describe(item, ("descripcion", "fecha", "proyecto_codigo", "proyecto_nombre")) for item in sources["distinciones"]])
    w.narrative(147, 147, [])
    sections = {"otras": [], "cursos": [], "gestion": [], "eventos": []}
    for item in sources["participaciones"]:
        value = describe(item, ("nombre_evento", "forma_participacion", "fecha", "investigador_nombre", "becario_nombre"))
        kind = normalized(item.get("nombre_evento"))
        category = "gestion" if "gestión interna" in kind or "gestion interna" in kind or "asamblea" in kind else (
            "eventos" if "organización" in kind or "organizacion" in kind else "cursos" if "curso" in kind or "taller" in kind else "otras")
        sections[category].append(value)
    w.narrative(150, 190, sections["otras"])
    w.narrative(192, 195, sections["cursos"])
    w.narrative(197, 204, sections["gestion"])
    w.narrative(206, 208, sections["eventos"])
    visitas = [describe(item, ("procedencia", "razon", "fecha", "tipo_visita_nombre")) for item in sources["visitas"]]
    w.set(148, "A", "6.2.- Visitantes del país y del extranjero", content=False)
    if visitas:
        w.set(148, "A", "6.2.- Visitantes del país y del extranjero:", content=False)
        w.insert(149, len(visitas), 144)
        first = w.row(149) - len(visitas)
        for index, paragraph in enumerate(visitas):
            w.sheet.row_dimensions[first + index].height = 24
            w.set_at(first + index, "A", paragraph)
    for start, end, category in ((212, 217, "nacional"), (221, 222, "internacional")):
        items = [item for item in sources["trabajos_reunion"] if meeting_category(item) == category]
        w.table(start, end, ["A", "B", "C", "D", "E", "F"], [[i, item.get("nombre_reunion"), item.get("procedencia"),
            civil_date(item.get("fecha_presentacion")), helpers._autores_texto(item.get("autores", [])),
            (item.get("titulo_trabajo") or "-") + ("\nEnlace: " + item["enlace"] if item.get("enlace") else "")]
            for i, item in enumerate(items, 1)])
    for header in (211, 220):
        w.set(header, "D", "Fecha de presentación", content=False)
        w.set(header, "E", "Autores", content=False)
    revistas = [item for item in sources["trabajos_revista"] if publication_category(item) == "revista"]
    w.table(227, 229, ["A", "B", "C", "D", "E", "F"], [[i, item.get("nombre_revista"), item.get("pais"), item.get("editorial"), item.get("issn"),
        (item.get("titulo_trabajo") or "-") + "\nAutores: " + helpers._autores_texto(item.get("autores", [])) +
        "\nFecha: " + helpers._format_date(civil_date(item.get("fecha_publicacion"))) +
        ("\nEnlace: " + item["enlace"] if item.get("enlace") else "")] for i, item in enumerate(revistas, 1)])
    w.narrative(233, 237, [describe(item, ("titulo_trabajo", "nombre_revista", "editorial", "pais", "issn", "fecha_publicacion", "autores", "enlace"))
                         for item in sources["trabajos_revista"] if publication_category(item) == "libro"])
    w.narrative(239, 249, [describe(item, ("titulo", "descripcion", "fecha_publicacion")) for item in sources["articulos"]], empty_row=240)
    w.narrative(251, 255, [describe(item, ("nombre_articulo", "organismo_registrante", "fecha_registro", "tipo_registro_nombre"))
                         for item in sources["registros"] if property_category(item) == "patente"])
    for start, end, category in ((258, 260, "intelectual"), (262, 264, "industrial")):
        items = [item for item in sources["registros"] if property_category(item) == category]
        w.narrative(start, end, [f"{item.get('nombre_articulo')} - {item.get('organismo_registrante')} - {helpers._format_date(civil_date(item.get('fecha_registro')))}" for item in items])
    # El grado del investigador no determina el nivel de la asignatura.
    w.set(266, "C", "Grado académico del investigador", content=False)
    w.set(266, "E", "Actividades docentes y cátedras (nivel no informado)", content=False)
    w.table(267, 272, ["A", "B", "C", "E"], [[i, item.get("investigador_nombre"), item.get("grado_academico_nombre") or "-",
        describe(item, ("curso", "institucion", "rol_actividad_nombre", "fecha_inicio", "fecha_fin"))]
        for i, item in enumerate(sources["actividades"], 1)])
    for start, end, category in ((278, 279, "tecnologia"), (284, 285, "idi"), (289, 289, "conocimientos"),
                                (293, 294, "asistencia"), (298, 298, "servicios"), (302, 304, "difusion")):
        items = [item for item in sources["transferencias"] if transfer_category(item) == category]
        w.table(start, end, ["A", "B", "D", "F", "G", "H"], [[i, item.get("denominacion"), helpers._join_dict_names(item.get("adoptantes"), "adoptante_nombre"),
            item.get("demandante"), importe_original(item, "monto"), item.get("descripcion_actividad")] for i, item in enumerate(items, 1)])
    for start, end, category in ((309, 314, "CORRIENTE"), (318, 319, "CAPITAL")):
        totals = {}
        for item in sources["erogaciones"]:
            movement = item.get("tipo_movimiento")
            if movement not in ("INGRESO", "EGRESO") or (movement == "EGRESO" and item.get("categoria_erogacion_codigo") not in ("CORRIENTE", "CAPITAL")):
                w.warnings.append("Movimiento sin clasificación contable: " + str(item.get("numero_movimiento") or item.get("id") or "sin referencia"))
                continue
            ingreso = item.get("tipo_movimiento") == "INGRESO"
            if (ingreso and category != "CORRIENTE") or (not ingreso and item.get("categoria_erogacion_codigo") != category):
                continue
            source = item.get("fuente_financiamiento_nombre") or "-"
            amount = money(item)
            if amount is None:
                w.warnings.append("Movimiento sin equivalencia ARS: " + str(item.get("numero_movimiento") or item.get("id") or "sin referencia"))
                continue
            entry = totals.setdefault(source, [Decimal(0), Decimal(0)])
            entry[0 if ingreso else 1] += amount
        w.table(start, end, ["A", "B", "C", "E"], [[i, name, values[0], values[1]] for i, (name, values) in enumerate(totals.items(), 1)])
        for row in range(w.row(start), w.row(start) + len(totals)):
            for col in ("C", "E"):
                w.sheet[f"{col}{row}"].number_format = '"ARS" #,##0.00'
    if w.warnings:
        w.set(306, "A", "11.- RESUMEN DE INGRESOS Y EGRESOS · Revisar movimientos excluidos en Detalle académico", content=False)
    plan_year = context.get("anio_programa")
    w.set(321, "A", "VI - PROGRAMA DE ACTIVIDADES" + (f" para {plan_year}" if plan_year else ""), content=False)
    w.narrative(322, 359, (context.get("programa_actividades") or "").split("\n\n"))
    write_academic_detail(w, sources, context, helpers, {
        "trabajos_reunion": meeting_category, "trabajos_revista": publication_category,
        "transferencias": transfer_category, "personal": personal_category,
        "becarios": lambda item: fellow_category(item, helpers), "registros": property_category,
    })
    return w.finish()
