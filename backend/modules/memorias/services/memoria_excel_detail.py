"""Detalle académico de snapshots, separado de la maquetación institucional."""
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from textwrap import wrap

from openpyxl.styles import Font, Alignment, Border, Side

MISSING = "Sin información registrada en esta versión."


LABELS = {
    "nombre_apellido": "Nombre y apellido", "fecha_alta_grupo": "Ingreso al grupo", "horas_semanales": "Horas semanales",
    "categoria_utn_nombre": "Categoría UTN", "programa_incentivos_nombre": "Programa de incentivos", "tipo_dedicacion_nombre": "Dedicación",
    "tipo_formacion_nombre": "Formación", "becas_percibidas": "Becas percibidas", "fuentes_financiamiento_beca": "Financiamiento de becas",
    "tipo_personal_nombre": "Tipo de personal", "codigo_proyecto": "Código del proyecto", "nombre_proyecto": "Proyecto",
    "descripcion_proyecto": "Descripción", "fecha_inicio": "Inicio", "fecha_fin": "Finalización",
    "logros_obtenidos": "Logros obtenidos", "dificultades_proyecto": "Dificultades", "monto_destinado": "Monto destinado (ARS)",
    "tipo_proyecto_nombre": "Tipo de proyecto", "fuente_financiamiento_nombre": "Fuente de financiamiento",
    "curso": "Curso / cátedra", "institucion": "Institución", "investigador_nombre": "Investigador",
    "becario_nombre": "Becario", "rol_actividad_nombre": "Rol docente", "grado_academico_nombre": "Grado académico del investigador",
    "historial_grados": "Grados y vigencias", "nombre_evento": "Evento", "forma_participacion": "Participación",
    "fecha": "Fecha", "titulo": "Título", "editorial": "Editorial", "anio": "Año", "autores": "Autores",
    "denominacion": "Denominación", "descripcion_breve": "Descripción", "fecha_incorporacion": "Incorporación",
    "monto_invertido": "Inversión", "moneda": "Moneda", "numero_movimiento": "Número de movimiento", "tipo_movimiento": "Movimiento",
    "monto": "Importe original", "tipo_cambio_aplicado": "Tipo de cambio a ARS", "monto_equivalente_ars": "Equivalente ARS",
    "fecha_cotizacion": "Fecha de cotización", "serie_bcra": "Serie BCRA", "categoria_erogacion_codigo": "Categoría de egreso",
    "categoria_erogacion_nombre": "Nombre de categoría", "equipamiento_denominacion": "Equipamiento relacionado",
    "numero_transferencia": "Número de transferencia", "demandante": "Demandante", "descripcion_actividad": "Actividad",
    "tipo_contrato_nombre": "Tipo de contrato", "adoptantes": "Adoptantes", "enlace": "Enlace",
    "titulo_trabajo": "Título del trabajo", "nombre_reunion": "Reunión científica", "procedencia": "Procedencia",
    "fecha_presentacion": "Presentación", "tipo_reunion_nombre": "Tipo de reunión", "alcance": "Alcance", "referato": "Referato",
    "nombre_revista": "Revista / libro", "issn": "ISSN / ISBN", "pais": "País", "fecha_publicacion": "Publicación",
    "tipo_revista_nombre": "Tipo de publicación", "descripcion": "Descripción", "proyecto_codigo": "Código del proyecto",
    "proyecto_nombre": "Proyecto", "nombre_articulo": "Denominación", "organismo_registrante": "Organismo registrante",
    "fecha_registro": "Registro", "tipo_registro_nombre": "Tipo de registro", "razon": "Motivo", "tipo_visita_nombre": "Tipo de visita",
    "cargo": "Cargo", "adoptante_nombre": "Adoptante", "rol": "Rol", "tipo": "Tipo",
}
DETAIL_SECTIONS = (
    ("investigadores", "Investigadores", "nombre_apellido fecha_alta_grupo horas_semanales categoria_utn_nombre programa_incentivos_nombre tipo_dedicacion_nombre"),
    ("personal", "Personal", "nombre_apellido tipo_personal_nombre fecha_alta_grupo horas_semanales"),
    ("becarios", "Becarios", "nombre_apellido tipo_formacion_nombre fecha_alta_grupo horas_semanales becas_percibidas fuentes_financiamiento_beca"),
    ("proyectos", "Proyectos de investigación", "codigo_proyecto nombre_proyecto tipo_proyecto_nombre descripcion_proyecto fecha_inicio fecha_fin logros_obtenidos dificultades_proyecto monto_destinado fuente_financiamiento_nombre"),
    ("actividades", "Docencia", "investigador_nombre curso institucion rol_actividad_nombre grado_academico_nombre fecha_inicio fecha_fin historial_grados"),
    ("participaciones", "Participaciones", "nombre_evento forma_participacion fecha investigador_nombre becario_nombre"),
    ("documentacion", "Documentación bibliográfica", "titulo autores editorial anio fecha"),
    ("equipamiento", "Equipamiento", "denominacion descripcion_breve fecha_incorporacion monto_invertido moneda"),
    ("erogaciones", "Movimientos financieros", "numero_movimiento fecha tipo_movimiento monto moneda tipo_cambio_aplicado monto_equivalente_ars fecha_cotizacion serie_bcra fuente_financiamiento_nombre categoria_erogacion_codigo categoria_erogacion_nombre equipamiento_denominacion"),
    ("transferencias", "Transferencias", "numero_transferencia denominacion tipo_contrato_nombre fecha_inicio fecha_fin demandante adoptantes descripcion_actividad monto moneda"),
    ("trabajos_reunion", "Trabajos en reuniones científicas", "titulo_trabajo nombre_reunion tipo_reunion_nombre alcance referato procedencia fecha_presentacion autores enlace"),
    ("trabajos_revista", "Publicaciones", "titulo_trabajo nombre_revista tipo_revista_nombre referato editorial pais issn fecha_publicacion autores enlace"),
    ("distinciones", "Distinciones", "descripcion fecha proyecto_codigo proyecto_nombre"),
    ("registros", "Registros y patentes", "nombre_articulo tipo_registro_nombre organismo_registrante fecha_registro"),
    ("articulos", "Divulgación", "titulo descripcion fecha_publicacion"),
    ("visitas", "Visitas", "procedencia razon tipo_visita_nombre fecha"),
)


def display(value):
    if value is None or value == "":
        return MISSING
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, list):
        return "\n".join(display(item) for item in value) or MISSING
    if isinstance(value, dict):
        # Los hijos del snapshot incluyen auditoría e IDs: no son contenido académico.
        if value.get("nombre_apellido"):
            name = value["nombre_apellido"]
            return f"{name} ({value['tipo']})" if value.get("tipo") else name
        return "; ".join(f"{LABELS[key]}: {display(val)}" for key, val in value.items()
                         if key in LABELS and val not in (None, "")) or MISSING
    converted = civil_date(value) if not isinstance(value, str) or len(value) == 10 else value
    if isinstance(converted, (date, datetime)):
        return converted.strftime("%d/%m/%Y")
    return str(value)


def describe(item, fields):
    return "\n".join(f"{LABELS[field]}: {display(item.get(field))}" for field in fields)


def write_academic_detail(writer, sources, context, helpers, classifiers):
    """Detalle explícito, sin consultar entidades vivas ni exportar auditoría o PII."""
    sheet = writer.workbook.create_sheet("Detalle académico")
    for column, width in (("A", 34), ("B", 35), ("C", 35), ("D", 35)):
        sheet.column_dimensions[column].width = width
    row = 1
    side = Side(style="thin", color="000000")
    border = Border(left=side, right=side, top=side, bottom=side)

    def line(label, value, *, heading=False, number_format=None):
        nonlocal row
        value = MISSING if value is None or value == "" else value
        if isinstance(value, (list, dict, bool)):
            value = display(value)
        # Cada fragmento ocupa su fila y permanece íntegro, incluso para textos
        # mayores que la altura máxima de una celda de Excel.
        chunks = [value]
        if isinstance(value, str):
            visual_lines = [part for line_text in value.splitlines(keepends=True) for part in
                            wrap(line_text, 80, replace_whitespace=False, drop_whitespace=False, expand_tabs=False)]
            chunks = ["".join(visual_lines[index:index + 18]) for index in range(0, len(visual_lines), 18)] or [value]
        for index, chunk in enumerate(chunks):
            first = sheet.cell(row, 1, label if not index else label + " (continuación)")
            sheet.merge_cells(start_row=row, end_row=row, start_column=2, end_column=4)
            cell = sheet.cell(row, 2, chunk)
            if isinstance(chunk, str):
                cell.data_type = "s"
            for target in (first, cell):
                target.font = Font(name="Calibri", size=11, bold=heading or target == first, color="FF000000")
                target.alignment = Alignment(vertical="top", wrap_text=True)
                target.border = border
                if heading:
                    target.fill = copy(writer.source["A3"].fill)
            if number_format:
                cell.number_format = number_format
            elif isinstance(chunk, (date, datetime)):
                cell.number_format = "dd/mm/yyyy"
            lines = sum(max(1, len(wrap(part, 80))) for part in str(chunk).split("\n"))
            label_lines = len(wrap(first.value, 26))
            sheet.row_dimensions[row].height = min(409, max(24, max(lines, label_lines) * 17 + 6))
            row += 1

    memoria, version = sources["memoria"], sources.get("version")
    line("Detalle académico", context["grupo"].get("nombre_sigla_grupo"), heading=True)
    line("Período", helpers._format_period(memoria.periodo_inicio, memoria.periodo_fin))
    line("Versión", getattr(version, "numero_version", None))
    line("Criterio", "Datos conservados al cerrar esta versión. Sin clasificar indica que no hay información suficiente para atribuir una sección institucional. Las sumas del formulario se expresan en ARS; un movimiento sin equivalencia ARS se conserva aquí y se excluye del resumen.")
    for warning in dict.fromkeys(writer.warnings):
        line("Revisión requerida", warning)
    line("Autoridades del período", len(context.get("directivos", [])), heading=True)
    for item in context.get("directivos", []):
        for field in ("nombre_apellido", "cargo", "fecha_inicio", "fecha_fin"):
            line(LABELS[field], civil_date(item.get(field)))
    for key, title, fields in DETAIL_SECTIONS:
        records = sources[key]
        line(title, f"{len(records)} registros", heading=True)
        for index, item in enumerate(records, 1):
            reference = f"Registro histórico {item['id']}" if item.get("id") is not None else "Registro de la versión"
            line(f"{title} · {index}", reference, heading=True)
            classifier = classifiers.get(key)
            category = classifier(item) if classifier else None
            if category is not None:
                line("Clasificación para el formulario", category)
            for field in fields.split():
                value = item.get(field)
                if field == "logros_obtenidos" and not value:
                    value = context.get("logros_proyectos", {}).get(str(item.get("proyecto_investigacion_id")))
                if field.startswith("fecha"):
                    value = civil_date(value)
                fmt = None
                if field in ("monto", "monto_invertido"):
                    value = Decimal(str(value)) if value is not None else None
                    fmt = f'"{item.get("moneda") or "ARS"}" #,##0.00'
                elif field in ("monto_destinado", "monto_equivalente_ars"):
                    value = Decimal(str(value)) if value is not None else None
                    fmt = '"ARS" #,##0.00'
                line(LABELS[field], value, number_format=fmt)
    sheet.freeze_panes = "B5"
    sheet.sheet_view.showGridLines = False
    sheet.print_area = f"A1:D{row - 1}"
    sheet.print_title_rows = "1:3"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0


def civil_date(value):
    if isinstance(value, str):
        try:
            return date.fromisoformat(value) if len(value) == 10 else value
        except ValueError:
            return value
    return value
