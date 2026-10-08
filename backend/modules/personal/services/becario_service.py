from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, fin_vigencia, resolver_horas_al_fin,
)
import builtins
from datetime import date, datetime

from extension import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, lazyload, selectinload
from modules.personal.services.identidad_service import asignar_identidad, conflicto_identidad_por_integridad
from modules.shared.services.text_validation import has_only_letters_and_spaces
from modules.personal.services.horas_validation import validar_horas_semanales as _validar_horas
from modules.shared.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError as ValueError,
)
from modules.personal.models.personal import Becario, TipoFormacion, BecarioHorasHistorial, BecarioMemoriaVersion
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date
from modules.recursos.models.becas import Beca, Beca_Becario
from modules.memorias.services.memoria_periodo_service import (
    validar_fecha_alta_grupo,
    estuvo_activo_en_periodo_memoria,
)


# =====================================================
# HELPERS
# =====================================================

def _validar_payload(data: dict):
    if not isinstance(data, dict) or not data:
        raise ValueError("Los datos no pueden estar vacios.")


def _validar_id_positivo(valor, campo: str, permitir_none: bool = False):
    if valor is None and permitir_none:
        return valor

    if not isinstance(valor, int) or valor <= 0:
        raise ValueError(f"El campo '{campo}' debe ser un entero positivo.", details={"fields": {campo: "Seleccione una opción válida"}})

    return valor


def _validar_user_id(user_id: int):
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("No pudimos procesar la solicitud. Intente nuevamente.")


def _validar_nombre(nombre: str):
    if not isinstance(nombre, str):
        raise ValueError("El nombre y apellido es obligatorio.", details={"fields": {"nombre_apellido": "Ingrese nombre y apellido"}})

    nombre = nombre.strip()

    if not nombre:
        raise ValueError("El nombre y apellido es obligatorio.", details={"fields": {"nombre_apellido": "Ingrese nombre y apellido"}})

    if not has_only_letters_and_spaces(nombre):
        raise ValueError("Use solo letras y espacios en nombre y apellido.", details={"fields": {"nombre_apellido": "Use solo letras y espacios en nombre y apellido"}})

    if len(nombre) > 120:
        raise ValueError("El nombre y apellido no puede superar los 120 caracteres.", details={"fields": {"nombre_apellido": "Use hasta 120 caracteres"}})

    return nombre


def _validar_proyectos_ids(proyectos_ids):
    if not isinstance(proyectos_ids, list):
        raise ValueError("Seleccione proyectos válidos.", details={"fields": {"proyectos": "Revise los proyectos seleccionados"}})

    ids_normalizados = []
    ids_vistos = set()

    for proyecto_id in proyectos_ids:
        proyecto_id = _validar_id_positivo(proyecto_id, "proyectos")

        if proyecto_id in ids_vistos:
            raise ValueError("Un proyecto está repetido.", details={"fields": {"proyectos": "Quite el proyecto repetido"}})

        ids_vistos.add(proyecto_id)
        ids_normalizados.append(proyecto_id)

    return ids_normalizados


def _obtener_proyectos_validos(proyectos_ids):
    if not proyectos_ids:
        return []

    proyectos = ProyectoInvestigacion.query.filter(
        ProyectoInvestigacion.id.in_(proyectos_ids)
    ).all()

    proyectos_activos = [
        proyecto
        for proyecto in proyectos
        if getattr(proyecto, "deleted_at", None) is None
    ]

    if len(proyectos_activos) != len(proyectos_ids):
        raise ValueError("Uno o más proyectos ya no están disponibles.", details={"fields": {"proyectos": "Quite los proyectos no disponibles y vuelva a intentar"}})

    return proyectos_activos


def _obtener_historiales_activos(becario):
    return [h for h in becario.historial_horas if h.fecha_fin is None]


def _obtener_historial_activo_unico(becario):
    historiales_activos = _obtener_historiales_activos(becario)

    if len(historiales_activos) > 1:
        raise ValueError("El becario tiene mas de un historial de horas activo.")

    return historiales_activos[0] if historiales_activos else None


def _resolver_horas_activas(becario):
    historial_activo = _obtener_historial_activo_unico(becario)
    return (
        historial_activo.horas_semanales
        if historial_activo else becario.horas_semanales
    )


def _resolver_becas_percibidas(becario, memoria_version=None):
    relaciones_activas = []
    for relacion in getattr(becario, "becas", []):
        beca = getattr(relacion, "beca", None)
        if beca is None:
            continue

        if memoria_version is not None:
            if not estuvo_activo_en_periodo_memoria(
                memoria_version,
                getattr(relacion, "fecha_inicio", None),
                fin_vigencia(relacion)
            ):
                continue
        elif getattr(relacion, "deleted_at", None) is not None:
            continue

        relaciones_activas.append(relacion)

    nombres_becas = sorted({
        relacion.beca.nombre_beca
        for relacion in relaciones_activas
        if getattr(relacion.beca, "nombre_beca", None)
    })
    fuentes = sorted({
        relacion.beca.fuente_financiamiento.nombre
        for relacion in relaciones_activas
        if getattr(relacion.beca, "fuente_financiamiento", None) is not None
        and getattr(relacion.beca.fuente_financiamiento, "nombre", None)
    })

    return {
        "becas_percibidas": ", ".join(nombres_becas),
        "fuentes_financiamiento_beca": ", ".join(fuentes)
    }


def _cerrar_historial(historial_activo):
    if historial_activo.fecha_inicio > date.today():
        raise ValueError("El historial activo tiene una fecha de inicio invalida.")

    historial_activo.fecha_fin = date.today()


def _get_activo_or_404(id: int):
    _validar_id_positivo(id, "id")

    becario = db.session.get(Becario, id)

    if not becario or becario.deleted_at is not None:
        raise NotFoundError("Becario no encontrado.")

    return becario


def _parsear_fecha_relacion(valor, campo, permitir_none=False):
    if valor in (None, "") and permitir_none:
        return None
    label = "inicio" if campo == "fecha_inicio" else "fin"
    if not isinstance(valor, str):
        raise ValueError("Revise la fecha de la beca.", details={"fields": {"becas": f"Ingrese la fecha de {label} en formato YYYY-MM-DD"}})
    try:
        fecha = datetime.strptime(valor, "%Y-%m-%d").date()
    except builtins.ValueError as exc:
        raise ValueError("Revise la fecha de la beca.", details={"fields": {"becas": f"Ingrese la fecha de {label} en formato YYYY-MM-DD"}}) from exc
    try:
        return validate_institutional_date(fecha, campo)
    except ValueError as exc:
        raise ValueError("Revise la fecha de la beca.", details={"fields": {"becas": f"Ingrese una fecha de {label} dentro del rango permitido"}}) from exc


def _sincronizar_becas(becario, becas_data, user_id):
    if not isinstance(becas_data, list):
        raise ValueError("Revise las becas seleccionadas.", details={"fields": {"becas": "Seleccione becas válidas"}})

    deseadas = {}
    for item in becas_data:
        if not isinstance(item, dict):
            raise ValueError("Revise las becas seleccionadas.", details={"fields": {"becas": "Revise las becas seleccionadas"}})
        beca_id = _validar_id_positivo(item.get("beca_id"), "beca_id")
        if beca_id in deseadas:
            raise ValueError("Una beca está repetida.", details={"fields": {"becas": "Quite la beca repetida"}})
        beca = db.session.get(Beca, beca_id)
        if not beca or beca.deleted_at is not None:
            raise ValueError("Una beca ya no está disponible.", details={"fields": {"becas": "Quite la beca no disponible y vuelva a intentar"}})
        fecha_inicio = _parsear_fecha_relacion(item.get("fecha_inicio"), "fecha_inicio")
        fecha_fin = _parsear_fecha_relacion(item.get("fecha_fin"), "fecha_fin", True)
        if fecha_fin is None:
            raise ValueError("La fecha de fin es obligatoria para registrar el plazo de la beca.", details={"fields": {"becas": "Ingrese la fecha de fin de la beca"}})
        if fecha_fin and fecha_fin < fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior al inicio.", details={"fields": {"becas": "Elija una fecha de fin posterior o igual al inicio"}})
        monto = item.get("monto_percibido")
        if monto is not None:
            try:
                monto = float(monto)
            except (TypeError, builtins.ValueError) as exc:
                raise ValueError("Revise el monto de la beca.", details={"fields": {"becas": "Ingrese un monto numérico válido"}}) from exc
            if monto < 0:
                raise ValueError("Revise el monto de la beca.", details={"fields": {"becas": "Ingrese un monto igual o mayor que cero"}})
        deseadas[beca_id] = (fecha_inicio, fecha_fin, monto)

    activas = {
        relacion.id_beca: relacion
        for relacion in getattr(becario, "becas", [])
        if relacion.deleted_at is None
    }

    for beca_id, relacion in activas.items():
        if beca_id not in deseadas:
            relacion.soft_delete(user_id)
            AuditoriaService.registrar_evento_relacion(
                "becario", becario.id, "becas", "desvincular",
                {"beca_id": beca_id}, user_id,
            )

    for beca_id, valores in deseadas.items():
        fecha_inicio, fecha_fin, monto = valores
        relacion = activas.get(beca_id)
        if relacion:
            anterior = (relacion.fecha_inicio, relacion.fecha_fin, relacion.monto_percibido)
            if anterior != valores:
                relacion.fecha_inicio = fecha_inicio
                relacion.fecha_fin = fecha_fin
                relacion.monto_percibido = monto
                relacion.mark_updated(user_id)
                AuditoriaService.registrar_evento_relacion(
                    "becario", becario.id, "becas", "actualizar",
                    {"beca_id": beca_id, "fecha_inicio": fecha_inicio,
                     "fecha_fin": fecha_fin, "monto_percibido": monto}, user_id,
                )
            continue
        db.session.add(Beca_Becario(
            id_beca=beca_id, id_becario=becario.id,
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            monto_percibido=monto, created_by=user_id,
        ))
        AuditoriaService.registrar_evento_relacion(
            "becario", becario.id, "becas", "vincular",
            {"beca_id": beca_id, "fecha_inicio": fecha_inicio,
             "fecha_fin": fecha_fin, "monto_percibido": monto}, user_id,
        )


# =====================================================
# CREATE
# =====================================================
def crear_becario(data: dict, user_id: int):
    _validar_payload(data)
    _validar_user_id(user_id)

    nombre = _validar_nombre(data.get("nombre_apellido"))
    horas = _validar_horas(data.get("horas_semanales"))
    tipo_formacion_id = _validar_id_positivo(
        data.get("tipo_formacion_id"), "tipo_formacion_id"
    )
    grupo_utn_id = _validar_id_positivo(
        data.get("grupo_utn_id"), "grupo_utn_id", permitir_none=True
    )
    proyectos_ids = _validar_proyectos_ids(data.get("proyectos", []))

    if not TipoFormacion.query.get(tipo_formacion_id):
        raise ValueError("Tipo de formacion invalido.")

    if grupo_utn_id and not GrupoInvestigacionUtn.query.get(grupo_utn_id):
        raise ValueError("Grupo UTN invalido.")

    becario = Becario(
        nombre_apellido=nombre,
        horas_semanales=horas,
        fecha_alta_grupo=validar_fecha_alta_grupo(
            data.get("fecha_alta_grupo")
        ),
        tipo_formacion_id=tipo_formacion_id,
        grupo_utn_id=grupo_utn_id,
        activo=True,
        created_by=user_id
    )
    asignar_identidad(becario, data, nueva=True)

    try:
        db.session.add(becario)
        db.session.flush()
    except IntegrityError as error:
        db.session.rollback()
        conflicto_identidad_por_integridad(error)

    historial = BecarioHorasHistorial(
        becario_id=becario.id,
        horas_semanales=horas,
        fecha_inicio=date.today(),
        fecha_fin=None,
        created_by=user_id
    )

    db.session.add(historial)

    if proyectos_ids:
        proyectos = _obtener_proyectos_validos(proyectos_ids)
        becario.participaciones_proyecto = proyectos

    if "becas" in data:
        try:
            _sincronizar_becas(becario, data["becas"], user_id)
        except Exception:
            db.session.rollback()
            raise

    try:
        db.session.commit()
        return becario
    except IntegrityError as error:
        db.session.rollback()
        conflicto_identidad_por_integridad(error)
    except Exception:
        db.session.rollback()
        raise


# =====================================================
# UPDATE
# =====================================================

def actualizar_becario(id: int, data: dict, user_id: int):
    _validar_payload(data)
    _validar_user_id(user_id)
    if "horas_semanales" in data:
        _validar_horas(data["horas_semanales"])

    becario = _get_activo_or_404(id)
    cambios = {}
    cambios.update(asignar_identidad(becario, data))

    if "activo" in data:
        if not isinstance(data["activo"], bool):
            raise ValueError("El campo 'activo' debe ser booleano.")

        if data["activo"] is False:
            raise ValueError("Para dar de baja un becario debe utilizarse el metodo eliminar.")

        becario.activo = data["activo"]

    if "nombre_apellido" in data:
        nuevo_valor = _validar_nombre(data["nombre_apellido"])
        cambio = AuditoriaService.construir_cambio(
            becario.nombre_apellido,
            nuevo_valor
        )
        if cambio:
            cambios["nombre_apellido"] = cambio
            becario.nombre_apellido = nuevo_valor

    if "horas_semanales" in data:
        horas = _validar_horas(data["horas_semanales"])
        historial_activo = _obtener_historial_activo_unico(becario)
        cambio = AuditoriaService.construir_cambio(
            becario.horas_semanales,
            horas
        )

        if not historial_activo:
            nuevo_historial = BecarioHorasHistorial(
                becario_id=becario.id,
                horas_semanales=horas,
                fecha_inicio=date.today(),
                fecha_fin=None,
                created_by=user_id
            )
            db.session.add(nuevo_historial)
        elif historial_activo.horas_semanales != horas:
            _cerrar_historial(historial_activo)

            nuevo_historial = BecarioHorasHistorial(
                becario_id=becario.id,
                horas_semanales=horas,
                fecha_inicio=date.today(),
                fecha_fin=None,
                created_by=user_id
            )

            db.session.add(nuevo_historial)

        if cambio:
            cambios["horas_semanales"] = cambio
            becario.horas_semanales = horas

    if "tipo_formacion_id" in data:
        tipo_formacion_id = _validar_id_positivo(
            data["tipo_formacion_id"], "tipo_formacion_id"
        )
        if not TipoFormacion.query.get(tipo_formacion_id):
            raise ValueError("Tipo de formacion invalido.")
        cambio = AuditoriaService.construir_cambio(
            becario.tipo_formacion_id,
            tipo_formacion_id
        )
        if cambio:
            cambios["tipo_formacion_id"] = cambio
            becario.tipo_formacion_id = tipo_formacion_id

    if "grupo_utn_id" in data:
        grupo_utn_id = _validar_id_positivo(
            data["grupo_utn_id"], "grupo_utn_id", permitir_none=True
        )
        if grupo_utn_id and not GrupoInvestigacionUtn.query.get(grupo_utn_id):
            raise ValueError("Grupo UTN invalido.")
        cambio = AuditoriaService.construir_cambio(
            becario.grupo_utn_id,
            grupo_utn_id
        )
        if cambio:
            cambios["grupo_utn_id"] = cambio
            becario.grupo_utn_id = grupo_utn_id

    if "fecha_alta_grupo" in data:
        nuevo_valor = validar_fecha_alta_grupo(data["fecha_alta_grupo"])
        cambio = AuditoriaService.construir_cambio(
            becario.fecha_alta_grupo,
            nuevo_valor
        )
        if cambio:
            cambios["fecha_alta_grupo"] = cambio
            becario.fecha_alta_grupo = nuevo_valor

    if "proyectos" in data:
        proyectos_ids = _validar_proyectos_ids(data["proyectos"])
        proyectos = _obtener_proyectos_validos(proyectos_ids)
        becario.participaciones_proyecto = proyectos

    if "becas" in data:
        try:
            _sincronizar_becas(becario, data["becas"], user_id)
            becario.mark_updated(user_id)
        except Exception:
            db.session.rollback()
            raise

    if cambios:
        becario.mark_updated(user_id)
        AuditoriaService.registrar_cambios(
            entidad="becario",
            registro_id=becario.id,
            cambios=cambios,
            user_id=user_id
        )

    try:
        db.session.commit()
        return becario
    except IntegrityError as error:
        db.session.rollback()
        conflicto_identidad_por_integridad(error)
    except Exception:
        db.session.rollback()
        raise


# =====================================================
# SOFT DELETE
# =====================================================

def eliminar_becario(id: int, user_id: int):
    _validar_user_id(user_id)

    becario = _get_activo_or_404(id)

    if not becario.activo:
        raise ConflictError("El becario ya se encuentra dado de baja.")

    historial_activo = _obtener_historial_activo_unico(becario)

    if historial_activo:
        _cerrar_historial(historial_activo)

    becario.activo = False
    becario.soft_delete(user_id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {
        "message": "Becario eliminado correctamente.",
        "id": becario.id
    }


# =====================================================
# LISTAR
# =====================================================

def _consulta_becarios(activos=None):
    query = Becario.query.options(
        lazyload("*"),
        joinedload(Becario.identidad),
        selectinload(Becario.historial_horas),
        joinedload(Becario.tipo_formacion),
        joinedload(Becario.grupo_utn).lazyload("*"),
    )

    if activos is None:
        activos = "true"

    activos = str(activos).strip().lower()

    if activos == "true":
        query = query.filter(Becario.deleted_at.is_(None))
    elif activos == "false":
        query = query.filter(Becario.deleted_at.isnot(None))
    elif activos == "all":
        pass
    else:
        query = query.filter(Becario.deleted_at.is_(None))

    return query.order_by(Becario.id.asc())


def listar_becarios(activos=None):
    return _consulta_becarios(activos).all()


def listar_becarios_paginado(page, per_page, activos="true", orden="asc"):
    query = _consulta_becarios(activos)
    if orden == "desc":
        query = query.order_by(None).order_by(Becario.id.desc())
    total = query.count()
    return query.offset((page - 1) * per_page).limit(per_page).all(), total


# =====================================================
# OBTENER POR ID
# =====================================================

def obtener_becario_por_id(id: int):
    _validar_id_positivo(id, "id")

    becario = db.session.get(Becario, id)
    if not becario:
        raise NotFoundError("Becario no encontrado.")

    return becario


def obtener_historial_becario(id: int):
    becario = obtener_becario_por_id(id)
    return AuditoriaService.obtener_historial_entidad(
        entidad="becario",
        registro_id=becario.id
    )


def snapshot_becarios_para_memoria_version(memoria_version, user_id):
    becarios = consultar_entidades_memoria(Becario, memoria_version)

    snapshots = []
    for becario in becarios:
        if not estuvo_activo_en_periodo_memoria(
            memoria_version,
            becario.fecha_alta_grupo,
            getattr(becario, "deleted_at", None)
        ):
            continue
        resumen_becas = _resolver_becas_percibidas(becario, memoria_version)
        snapshot = BecarioMemoriaVersion(
            memoria_version_id=memoria_version.id,
            becario_id=becario.id,
            nombre_apellido=becario.nombre_apellido,
            fecha_alta_grupo=becario.fecha_alta_grupo,
            horas_semanales=resolver_horas_al_fin(becario, memoria_version),
            tipo_formacion_id=becario.tipo_formacion_id,
            tipo_formacion_nombre=(
                becario.tipo_formacion.nombre
                if becario.tipo_formacion else None
            ),
            grupo_utn_id=becario.grupo_utn_id,
            grupo_utn_nombre=(
                becario.grupo_utn.nombre_sigla_grupo
                if becario.grupo_utn else None
            ),
            becas_percibidas=resumen_becas["becas_percibidas"],
            fuentes_financiamiento_beca=resumen_becas["fuentes_financiamiento_beca"],
            created_by=user_id
        )
        db.session.add(snapshot)
        snapshots.append(snapshot)

    return snapshots


def obtener_snapshots_becarios_por_memoria_version(memoria_version_id):
    snapshots = (
        BecarioMemoriaVersion.query
        .filter(
            BecarioMemoriaVersion.memoria_version_id == memoria_version_id,
            BecarioMemoriaVersion.deleted_at.is_(None)
        )
        .order_by(BecarioMemoriaVersion.nombre_apellido.asc())
        .all()
    )

    return [snapshot.serialize() for snapshot in snapshots]
