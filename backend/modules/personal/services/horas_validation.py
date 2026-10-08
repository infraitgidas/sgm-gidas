from modules.shared.exceptions import ValidationError

MAX_HORAS_SEMANALES = 7 * 24


def validar_horas_semanales(horas):
    if isinstance(horas, bool) or not isinstance(horas, int) or not 1 <= horas <= MAX_HORAS_SEMANALES:
        message = "Las horas semanales deben ser un número entero entre 1 y 168."
        raise ValidationError(message, details={"fields": {"horas_semanales": message}})
    return horas
