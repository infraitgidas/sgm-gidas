from modules.shared.exceptions import ValidationError


def validar_moneda(value):
    if not isinstance(value, str) or value not in {"ARS", "USD"}:
        raise ValidationError(
            "Revise los campos indicados e intente nuevamente.",
            details={"fields": {"moneda": "Seleccione ARS o USD."}},
        )
    return value
