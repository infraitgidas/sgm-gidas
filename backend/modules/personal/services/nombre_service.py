"""Nombres estructurados con compatibilidad para registros historicos."""
from modules.shared.exceptions import ValidationError
from modules.shared.services.text_validation import has_only_letters_and_spaces
from modules.shared.services.auditoria_service import AuditoriaService


def preparar_nombre(data, entidad=None):
    data = dict(data)
    if entidad is not None and not any(campo in data for campo in ("nombre", "apellido")):
        if entidad.nombre and entidad.apellido and "nombre_apellido" in data:
            if data["nombre_apellido"] != entidad.nombre_apellido:
                raise ValidationError("Modifique nombre y apellido por separado.")
        return data
    for campo in ("nombre", "apellido"):
        valor = data.get(campo, getattr(entidad, campo, None))
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Complete nombre y apellido.", details={"fields": {campo: "Complete este campo."}})
        valor = " ".join(valor.split())
        if len(valor) > 60 or not has_only_letters_and_spaces(valor):
            raise ValidationError("Revise nombre y apellido.", details={"fields": {campo: "Use solo letras y espacios, hasta 60 caracteres."}})
        data[campo] = valor
    data["nombre_apellido"] = f'{data["nombre"]} {data["apellido"]}'
    if len(data["nombre_apellido"]) > 120:
        raise ValidationError("Nombre y apellido deben sumar hasta 120 caracteres.")
    return data


def asignar_nombre(entidad, data):
    cambios = {}
    for campo in ("nombre", "apellido"):
        if campo in data:
            cambio = AuditoriaService.construir_cambio(getattr(entidad, campo), data[campo])
            if cambio:
                cambios[campo] = cambio
                setattr(entidad, campo, data[campo])
    return cambios


def nombre_para_memoria(persona):
    if getattr(persona, "nombre", None) and getattr(persona, "apellido", None):
        return f"{persona.nombre}, {persona.apellido.upper()}"
    return persona.nombre_apellido
