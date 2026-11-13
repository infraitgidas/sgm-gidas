"""Corrección transaccional de clase conservando la identidad de la persona."""
from datetime import date
from sqlalchemy import select, update

from extension import db
from modules.personal.models.personal import (
    Personal, Becario, Investigador, PersonalHorasHistorial,
    BecarioHorasHistorial, InvestigadorHorasHistorial,
    PersonalMemoriaVersion, BecarioMemoriaVersion, InvestigadorMemoriaVersion,
)
from modules.personal.services import personal_service as reglas
from modules.personal.services.becario_service import _sincronizar_becas
from modules.personal.services.identidad_service import asignar_identidad, conflicto_identidad_por_integridad
from modules.personal.services.nombre_service import preparar_nombre, asignar_nombre
from modules.personal.services.historial_service import CATALOGOS
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.auditoria_service import AuditoriaService
from sqlalchemy.exc import IntegrityError


CLASES = {
    "personal": (Personal, PersonalHorasHistorial),
    "becario": (Becario, BecarioHorasHistorial),
    "investigador": (Investigador, InvestigadorHorasHistorial),
}
ETIQUETAS = {"personal": "Personal de apoyo, técnico o administrativo",
             "becario": "Becario", "investigador": "Investigador"}
CAMPOS_CLASE = {
    "personal": {"tipo_personal_id": reglas._validar_tipo_personal},
    "becario": {"tipo_formacion_id": reglas._validar_tipo_formacion},
    "investigador": {"tipo_dedicacion_id": reglas._validar_tipo_dedicacion,
                     "categoria_utn_id": reglas._validar_categoria_utn,
                     "programa_incentivos_id": reglas._validar_programa_incentivos},
}
SNAPSHOTS = {"personal": PersonalMemoriaVersion, "becario": BecarioMemoriaVersion,
             "investigador": InvestigadorMemoriaVersion}


def _vincular_fotos_heredadas(rol, origen):
    """Completa solo referencias de fotos antiguas que no tenían DNI al generarse."""
    tabla = SNAPSHOTS[rol].__table__
    filtro = tabla.c[f"{rol}_id"] == origen.id
    if db.session.execute(select(tabla.c.id).where(
        filtro, tabla.c.identidad_id.is_not(None), tabla.c.identidad_id != origen.identidad_id
    ).limit(1)).first():
        raise ConflictError("La identidad histórica del integrante requiere revisión. Verifique sus datos antes de intentar nuevamente.")
    db.session.execute(update(tabla).where(filtro, tabla.c.identidad_id.is_(None)).values(identidad_id=origen.identidad_id))


def _validar_sin_dependencias(origen, horas_model):
    # Incluye FKs sin relationship ORM y vínculos operativos dados de baja.
    # Ninguna asociación se elimina por cascada al corregir la clase.
    for tabla in db.metadata.tables.values():
        if tabla is horas_model.__table__:
            continue
        for fk in tabla.foreign_keys:
            if fk.column.table is origen.__table__ and db.session.execute(
                select(fk.parent).where(fk.parent == origen.id).limit(1)
            ).first():
                raise ConflictError("No se puede cambiar la clase porque el integrante tiene vínculos o antecedentes registrados. Revise sus becas, proyectos y antecedentes desde el detalle. Los vínculos históricos deben conservarse.")


def reclasificar_personal(rol, registro_id, data, user_id):
    reglas._validar_user_id(user_id)
    reglas._validar_id_positivo(registro_id, "id")
    if not isinstance(data, dict) or rol not in CLASES:
        raise ValidationError("Seleccione una clase de personal válida.")
    destino_rol = data.get("clase_destino")
    if not isinstance(destino_rol, str) or destino_rol not in CLASES or destino_rol == rol:
        raise ValidationError("Seleccione una clase destino diferente de la actual.")
    comunes = {"nombre", "apellido", "nombre_apellido", "dni", "cuil", "horas_semanales", "fecha_alta_grupo", "grupo_utn_id", "activo"}
    permitidos = comunes | set(CAMPOS_CLASE[destino_rol]) | {"clase_destino"}
    if destino_rol == "becario":
        permitidos.add("becas")
    if set(data) - permitidos or data.get("activo", True) is not True:
        raise ValidationError("Revise los campos de la clase destino e intente nuevamente.")
    modelo, horas_origen = CLASES[rol]
    destino_modelo, horas_destino = CLASES[destino_rol]
    try:
        # El lock del padre impide cambios simultáneos y nuevas FKs durante el traslado.
        origen = modelo.query.filter_by(id=registro_id).with_for_update(of=modelo).populate_existing().first()
        if origen is None:
            raise NotFoundError("Personal no encontrado.")
        if not origen.activo or origen.deleted_at is not None:
            raise ConflictError("Reactive el integrante antes de cambiar su clase.")
        _validar_sin_dependencias(origen, horas_origen)
        horas_actuales = reglas._resolver_horas_activas(origen)
        valores = {campo: getattr(origen, campo) for campo in comunes if hasattr(origen, campo) and campo not in {"dni", "cuil"}}
        valores.update({campo: valor for campo, valor in data.items() if campo in comunes})
        if "horas_semanales" not in data:
            valores["horas_semanales"] = horas_actuales
        valores = preparar_nombre(valores, origen)
        valores["horas_semanales"] = reglas._validar_horas(valores["horas_semanales"])
        valores["grupo_utn_id"] = reglas._validar_grupo_utn(valores["grupo_utn_id"], obligatorio=True)
        valores["fecha_alta_grupo"] = reglas.validar_fecha_alta_grupo(valores["fecha_alta_grupo"].isoformat() if hasattr(valores["fecha_alta_grupo"], "isoformat") else valores["fecha_alta_grupo"])
        especificos = {}
        for campo, validar in CAMPOS_CLASE[destino_rol].items():
            especificos[campo] = validar(data.get(campo))
        # Las referencias de destino deben estar disponibles también al reclasificar.
        for campo in ("tipo_formacion_id", "tipo_dedicacion_id", "categoria_utn_id", "programa_incentivos_id"):
            if especificos.get(campo):
                referencia = db.session.get(CATALOGOS[campo][0], especificos[campo])
                if not referencia.activo or referencia.deleted_at is not None:
                    raise ValidationError("Seleccione una referencia activa.", details={"fields": {campo: "Seleccione una referencia activa."}})
        anterior = origen.serialize()
        cambios = asignar_identidad(origen, data if origen.identidad else valores, nueva=origen.identidad is None)
        destino = destino_modelo(
            **{campo: valores[campo] for campo in ("nombre_apellido", "horas_semanales", "grupo_utn_id", "fecha_alta_grupo")},
            **especificos, identidad=origen.identidad, activo=True,
            created_by=origen.created_by, created_at=origen.created_at,
        )
        asignar_nombre(destino, valores)
        destino.mark_updated(user_id)
        db.session.add(destino)
        db.session.flush()
        _vincular_fotos_heredadas(rol, origen)
        # Conserva todos los intervalos de horas, no solo el vigente.
        for historial in origen.historial_horas:
            copia = {c.name: getattr(historial, c.name) for c in horas_origen.__table__.columns
                     if c.name not in {"id", f"{rol}_id"}}
            db.session.add(horas_destino(**copia, **{f"{destino_rol}_id": destino.id}))
        for evento in AuditoriaCampo.query.filter_by(entidad=rol, registro_id=origen.id).all():
            evento.entidad, evento.registro_id = destino_rol, destino.id
        for campo in comunes - {"dni", "cuil", "activo"}:
            cambio = AuditoriaService.construir_cambio(anterior.get(campo), getattr(destino, campo))
            if cambio:
                cambios[campo] = cambio
        cambios["clase_registro"] = AuditoriaService.construir_cambio(ETIQUETAS[rol], ETIQUETAS[destino_rol])
        # Guarda los atributos abandonados y los nuevos para reconstruir la corrección.
        for campo in set(CAMPOS_CLASE[rol]) | set(CAMPOS_CLASE[destino_rol]):
            cambio = AuditoriaService.construir_cambio(getattr(origen, campo, None), getattr(destino, campo, None))
            if cambio:
                cambios[campo] = cambio
        AuditoriaService.registrar_cambios(destino_rol, destino.id, cambios, user_id)
        db.session.delete(origen)
        db.session.flush()
        if destino_rol == "becario" and "becas" in data:
            _sincronizar_becas(destino, data["becas"], user_id)
        # Aplica la misma regla temporal de edición sin commits intermedios.
        if anterior["horas_semanales"] != destino.horas_semanales or not destino.historial_horas:
            for historial in destino.historial_horas:
                if historial.fecha_fin is None:
                    historial.fecha_fin = date.today()
            db.session.add(horas_destino(**{f"{destino_rol}_id": destino.id}, horas_semanales=destino.horas_semanales,
                                        fecha_inicio=date.today(), created_by=user_id))
        db.session.commit()
        return {**destino.serialize(), "rol": destino_rol}
    except IntegrityError as error:
        db.session.rollback()
        conflicto_identidad_por_integridad(error)
    except Exception:
        db.session.rollback()
        raise
