from datetime import date, datetime, timezone

from modules.shared.exceptions import ValidationError


INSTITUTIONAL_MIN_DATE = date(2010, 1, 1)


def validate_institutional_date(
    value: date | datetime,
    field: str = "fecha",
    *,
    allow_future: bool = True,
):
    """Valida fechas de entidades contra el rango temporal institucional."""
    civil_date = value.date() if isinstance(value, datetime) else value

    if civil_date < INSTITUTIONAL_MIN_DATE:
        raise ValidationError(
            f"El campo '{field}' debe ser igual o posterior al 01/01/2010"
        )

    if not allow_future and civil_date > date.today():
        raise ValidationError(f"El campo '{field}' no puede ser futuro")

    return value


def serialize_temporal(value):
    """Serializa fechas civiles sin zona e instantes datetime en UTC explicito."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            utc_value = value.replace(tzinfo=timezone.utc)
        else:
            utc_value = value.astimezone(timezone.utc)

        return utc_value.isoformat().replace("+00:00", "Z")

    if isinstance(value, date):
        return value.isoformat()

    return value
