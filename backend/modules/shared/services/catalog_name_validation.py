from modules.shared.exceptions import ValidationError
from modules.shared.services.text_validation import has_letter


def validar_nombre_descriptivo(nombre: str, campo: str = "nombre") -> None:
    """Reject nonempty catalog labels without any Unicode letter."""
    if nombre and not has_letter(nombre):
        raise ValidationError(
            "El nombre debe contener al menos una letra.",
            details={"fields": {campo: "Ingrese un nombre con al menos una letra."}},
        )
