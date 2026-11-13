"""Validación de clasificación explícita, sin inferir datos históricos."""
from modules.shared.exceptions import ValidationError


def validar_clasificacion(data, *, reunion=False):
    resultado = {}
    errores = {}
    if "referato" in data:
        valor = data["referato"]
        if valor is not None and type(valor) is not bool:
            errores["referato"] = "Seleccione Sí, No o Sin informar."
        else:
            resultado["referato"] = valor
    if reunion and "alcance" in data:
        valor = data["alcance"]
        if valor is not None and (not isinstance(valor, str) or valor not in ("nacional", "internacional")):
            errores["alcance"] = "Seleccione Nacional, Internacional o Sin informar."
        else:
            resultado["alcance"] = valor
    if errores:
        raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": errores})
    return resultado
