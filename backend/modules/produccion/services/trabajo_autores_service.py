"""Validación y sincronización sin commits: la transacción pertenece al trabajo."""
from extension import db
from modules.personal.models.personal import Investigador, Becario
from modules.shared.exceptions import ValidationError, NotFoundError
from modules.shared.services.auditoria_service import AuditoriaService

MODELOS_AUTORES = {"investigador": Investigador, "becario": Becario}


def validar_referencias(autores):
    if not isinstance(autores, list):
        raise ValidationError("Autores debe ser una lista", details={"fields": {"autores": "Seleccione integrantes autores."}})
    vistos = set()
    referencias = []
    for autor in autores:
        if not isinstance(autor, dict):
            raise ValidationError("Autor inválido", details={"fields": {"autores": "Revise los autores seleccionados"}})
        rol, identificador = autor.get("rol"), autor.get("id")
        if not isinstance(rol, str) or rol not in MODELOS_AUTORES or type(identificador) is not int or identificador <= 0:
            raise ValidationError("Los autores deben ser investigadores o becarios con id entero positivo",
                                  details={"fields": {"autores": "Seleccione únicamente investigadores o becarios."}})
        clave = (rol, identificador)
        if clave in vistos:
            raise ValidationError("No se permiten autores duplicados", details={"fields": {"autores": "Quite el autor repetido"}})
        vistos.add(clave)
        referencias.append(clave)
    return referencias


def validar_autores(autores, existentes=()):
    referencias = validar_referencias(autores)
    if not referencias:
        raise ValidationError(
            "Debe seleccionar al menos un autor",
            details={"fields": {"autores": "Agregue al menos un autor."}},
        )
    actuales = {(a.rol, a.integrante.id) for a in existentes}
    resultado = []
    for rol, identificador in referencias:
        persona = db.session.get(MODELOS_AUTORES[rol], identificador)
        if persona is None:
            raise NotFoundError("Uno o más autores ya no están disponibles", details={"fields": {"autores": "Quite los autores no disponibles y vuelva a intentar"}})
        # Una asociación histórica puede conservarse; no se permiten altas inactivas.
        if (rol, identificador) not in actuales and (persona.deleted_at is not None or not persona.activo):
            raise ValidationError("Solo se pueden agregar integrantes activos y no eliminados", details={"fields": {"autores": "Seleccione autores activos"}})
        resultado.append((rol, persona))
    return resultado


def sincronizar_autores(trabajo, autores, modelo, entidad, user_id):
    actuales = {(a.rol, a.integrante.id): a for a in trabajo.autorias}
    nuevas = {(rol, persona.id): persona for rol, persona in autores}
    hubo_cambios = False
    for clave, asociacion in actuales.items():
        if clave not in nuevas:
            detalle = asociacion.serialize()
            trabajo.autorias.remove(asociacion)
            AuditoriaService.registrar_evento_relacion(entidad=entidad, registro_id=trabajo.id,
                relacion="autores", accion="desvincular", detalle=detalle, user_id=user_id)
            hubo_cambios = True
    for (rol, identificador), persona in nuevas.items():
        if (rol, identificador) not in actuales:
            asociacion = modelo(**{f"{rol}_id": identificador, rol: persona})
            trabajo.autorias.append(asociacion)
            AuditoriaService.registrar_evento_relacion(entidad=entidad, registro_id=trabajo.id,
                relacion="autores", accion="vincular", detalle=asociacion.serialize(), user_id=user_id)
            hubo_cambios = True
    if hubo_cambios:
        trabajo.mark_updated(user_id)
    return hubo_cambios


def filtrar_por_autor(query, trabajo_modelo, autor_modelo, filtros):
    rol, identificador = filtros.get("autor_rol"), filtros.get("autor_id")
    if rol is None and identificador is None:
        return query
    try:
        identificador = int(identificador)
    except (TypeError, ValueError):
        raise ValidationError("El filtro de autor requiere rol e id válidos")
    validar_referencias([{"rol": rol, "id": identificador}])
    return query.filter(trabajo_modelo.autorias.any(getattr(autor_modelo, f"{rol}_id") == identificador))
