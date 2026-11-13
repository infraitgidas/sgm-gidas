from datetime import date

from modules.memorias.services.memoria_periodo_service import validar_fecha_alta_grupo as validar_fecha_institucional
from modules.shared.exceptions import ValidationError


def validar_fecha_alta_grupo(valor):
    fecha = validar_fecha_institucional(valor)
    if fecha > date.today():
        mensaje = "Ingrese una fecha de alta que no sea futura."
        raise ValidationError(mensaje, details={"fields": {"fecha_alta_grupo": mensaje}})
    return fecha
