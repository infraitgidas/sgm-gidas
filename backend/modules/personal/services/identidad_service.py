"""Validacion y asignacion de DNI/CUIL para las tres variantes de Personal."""

import re

from extension import db
from modules.personal.models.identidad import IdentidadPersonal
from modules.shared.exceptions import ConflictError, ValidationError
from modules.shared.services.auditoria_service import AuditoriaService


_DNI = re.compile(r"[0-9]{7,8}\Z")
_CUIL = re.compile(r"([0-9]{2})-([0-9]{8})-([0-9])\Z")
_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _error(campo, mensaje):
    raise ValidationError(
        "Revise los campos indicados e intente nuevamente.",
        details={"fields": {campo: mensaje}},
    )


def validar_dni(valor):
    if not isinstance(valor, str) or not _DNI.fullmatch(valor):
        _error("dni", "Ingrese un DNI de 7 u 8 digitos, sin puntos.")
    return valor


def validar_cuil(valor, dni):
    match = _CUIL.fullmatch(valor) if isinstance(valor, str) else None
    if not match:
        _error("cuil", "Ingrese el CUIL con formato XX-XXXXXXXX-X.")
    if match.group(2) != dni.zfill(8):
        _error("cuil", "El numero central del CUIL debe coincidir con el DNI.")
    numeros = [int(digito) for digito in match.group(1) + match.group(2)]
    digito = 11 - sum(numero * peso for numero, peso in zip(numeros, _PESOS)) % 11
    esperado = 0 if digito == 11 else 9 if digito == 10 else digito
    if int(match.group(3)) != esperado:
        _error("cuil", "El digito verificador del CUIL no es valido.")
    return valor


def asignar_identidad(entidad, data, *, nueva=False):
    """Asigna la identidad y devuelve cambios de campos para el historial."""
    if not nueva and "dni" not in data and "cuil" not in data:
        return {}
    anterior = entidad.identidad
    if anterior is None and ("dni" not in data or "cuil" not in data):
        _error("dni" if "dni" not in data else "cuil", "Complete DNI y CUIL para guardar.")
    dni = validar_dni(data.get("dni", anterior.dni if anterior else None))
    cuil = validar_cuil(data.get("cuil", anterior.cuil if anterior else None), dni)

    otra = IdentidadPersonal.query.filter(
        IdentidadPersonal.dni == dni,
        IdentidadPersonal.id != (anterior.id if anterior else -1),
    ).first()
    if otra:
        raise ConflictError("El DNI ya esta registrado.", details={"fields": {"dni": "El DNI ya esta registrado."}})
    otra = IdentidadPersonal.query.filter(
        IdentidadPersonal.cuil == cuil,
        IdentidadPersonal.id != (anterior.id if anterior else -1),
    ).first()
    if otra:
        raise ConflictError("El CUIL ya esta registrado.", details={"fields": {"cuil": "El CUIL ya esta registrado."}})

    cambios = {}
    for campo, nuevo in (("dni", dni), ("cuil", cuil)):
        cambio = AuditoriaService.construir_cambio(getattr(anterior, campo) if anterior else None, nuevo)
        if cambio:
            cambios[campo] = cambio
    if anterior:
        anterior.dni, anterior.cuil = dni, cuil
    else:
        entidad.identidad = IdentidadPersonal(dni=dni, cuil=cuil)
    return cambios


def conflicto_identidad_por_integridad(error):
    """Traduce solo las colisiones de identidad; conserva otras restricciones."""
    mensaje = str(getattr(error, "orig", error)).lower()
    if "identidad_personal" not in mensaje:
        raise error
    campo = "cuil" if "cuil" in mensaje else "dni"
    nombre = campo.upper()
    raise ConflictError(
        f"El {nombre} ya esta registrado.",
        details={"fields": {campo: f"El {nombre} ya esta registrado."}},
    ) from error
