"""Stable API field keys and public labels for legacy domain validators."""
import re


FIELD_LABELS = {
    "codigo_proyecto": "código del proyecto", "nombre_proyecto": "nombre del proyecto",
    "tipo_proyecto_id": "tipo de proyecto", "fecha_inicio": "fecha de inicio",
    "fecha_fin": "fecha de finalización", "fecha_desde": "fecha desde", "fecha_hasta": "fecha hasta",
    "fuente_financiamiento_id": "fuente de financiamiento", "grupo_utn_id": "grupo",
    "grupo_id": "grupo", "id_grupo": "grupo", "investigador_id": "investigador",
    "id_investigador": "investigador", "id_becario": "becario", "becario_id": "becario",
    "id_proyecto": "proyecto", "proyecto_id": "proyecto", "beca_id": "beca",
    "nombre_apellido": "nombre y apellido", "horas_semanales": "horas semanales",
    "tipo_personal_id": "tipo de personal", "tipo_formacion_id": "tipo de formación",
    "tipo_dedicacion_id": "tipo de dedicación", "categoria_utn_id": "categoría UTN",
    "programa_incentivos_id": "programa de incentivos", "fecha_alta_grupo": "fecha de alta en el grupo",
    "es_coordinador": "coordinador", "monto_destinado": "monto destinado",
    "descripcion_proyecto": "descripción del proyecto", "dificultades_proyecto": "dificultades del proyecto",
    "nombre_usuario": "nombre de usuario", "mail": "correo electrónico", "rol_id": "rol",
    "password": "contraseña", "password_actual": "contraseña actual",
    "password_nueva": "nueva contraseña", "password_confirmacion": "confirmación de contraseña",
    "nombre": "nombre", "descripcion": "descripción", "denominacion": "denominación",
    "descripcion_breve": "descripción breve", "monto_invertido": "monto invertido",
    "fecha_incorporacion": "fecha de incorporación", "monto_percibido": "monto percibido",
    "tipo_erogacion_id": "tipo de erogación", "numero_erogacion": "número de erogación",
    "monto_erogacion": "monto de erogación", "fecha_erogacion": "fecha de erogación",
    "numero_transferencia": "número de transferencia", "tipo_contrato_id": "tipo de contrato",
    "descripcion_actividad": "descripción de la actividad", "demandante": "demandante",
    "titulo": "título", "editorial": "editorial", "anio": "año", "anios": "años", "fecha": "fecha",
    "fecha_publicacion": "fecha de publicación", "nombre_revista": "nombre de la revista",
    "pais": "país", "issn": "ISSN", "tipo_id": "tipo", "nombre_articulo": "nombre del artículo",
    "organismo_registrante": "organismo registrante", "fecha_registro": "fecha de registro",
    "tipo_registro_id": "tipo de registro", "grado_academico_id": "grado académico",
    "rol_actividad_id": "rol de la actividad", "institucion": "institución", "curso": "curso",
    "evento": "evento", "nombre_evento": "nombre del evento", "forma_participacion": "forma de participación",
    "fecha_participacion": "fecha de participación", "facultad_regional": "facultad regional",
    "nombre_sigla_grupo": "nombre y sigla del grupo", "correo_electronico": "correo electrónico",
    "objetivos": "objetivos", "cargo_id": "cargo", "fecha_alta": "fecha de alta", "fecha_baja": "fecha de baja",
    "periodo_inicio": "período de inicio", "periodo_fin": "período de fin", "fecha_apertura": "fecha de apertura",
    "fecha_cierre": "fecha de cierre", "activo": "estado activo", "cerrado": "estado cerrado",
    "dni": "DNI", "autores": "autores", "investigadores": "investigadores", "becarios": "becarios",
    "solo_becarios_con_beca_activa": "becarios con beca activa",
}
ACCENTS = {
    "sesion": "sesión", "accion": "acción", "informacion": "información", "operacion": "operación",
    "tamano": "tamaño", "Envie": "Envíe", "vacio": "vacío", "vacia": "vacía", "vacios": "vacíos",
    "vacias": "vacías", "invalido": "inválido", "invalida": "inválida", "invalidos": "inválidos",
    "invalidas": "inválidas", "numero": "número", "numerico": "numérico", "numerica": "numérica",
    "investigacion": "investigación", "publicacion": "publicación", "academico": "académico",
    "descripcion": "descripción", "pais": "país", "contrasena": "contraseña", "categoria": "categoría",
    "formacion": "formación", "participacion": "participación", "alfanumerico": "alfanumérico",
}
INTERNAL_DETAIL = re.compile(
    r"(?i)(traceback|sqlalchemy|psycopg|sqlite|postgres(?:ql)?|password\s*=|"
    r"SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+.+\s+SET|DELETE\s+FROM|"
    r"\b(?:table|column|constraint)\b|https?://|[A-Za-z]:[\\/])"
)
INTERNAL_KEY = re.compile(r"\b[a-zA-Z]+(?:_[a-zA-Z0-9]+)+\b")


def public_message(message, fallback):
    if not isinstance(message, str) or INTERNAL_DETAIL.search(message):
        return fallback
    text = message.strip()
    for key in sorted(FIELD_LABELS, key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(key)}(?!\w)", FIELD_LABELS[key], text)
    if INTERNAL_KEY.search(text):
        return fallback
    for word, accented in ACCENTS.items():
        text = re.sub(rf"\b{word}\b", accented, text)
    return text or fallback
