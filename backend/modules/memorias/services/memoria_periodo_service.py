from datetime import date, datetime

from modules.shared.exceptions import ValidationError
from modules.shared.services.date_time import validate_institutional_date


def validar_fecha_alta_grupo(
    valor,
    campo: str = "fecha_alta_grupo",
    permitir_none: bool = False
):
    if valor in (None, ""):
        if permitir_none:
            return None
        raise ValidationError(
            f"El campo '{campo}' es obligatorio y debe tener formato YYYY-MM-DD"
        )

    if isinstance(valor, date) and not isinstance(valor, datetime):
        return validate_institutional_date(valor, campo)

    if isinstance(valor, str):
        try:
            return validate_institutional_date(
                datetime.strptime(valor.strip(), "%Y-%m-%d").date(), campo
            )
        except ValueError:
            pass

    raise ValidationError(
        f"El campo '{campo}' es obligatorio y debe tener formato YYYY-MM-DD"
    )


def esta_en_periodo_memoria(memoria_version, fecha_referencia):
    if fecha_referencia is None:
        return False

    memoria = getattr(memoria_version, "memoria", None)
    if memoria is None:
        # Permite tests unitarios aislados donde la version se instancia sin
        # relacion cargada. En runtime la version siempre conoce a su memoria.
        return True

    periodo_inicio = getattr(memoria, "periodo_inicio", None)
    periodo_fin = getattr(memoria, "periodo_fin", None)

    if periodo_inicio is None or periodo_fin is None:
        return True

    return periodo_inicio <= fecha_referencia <= periodo_fin


def _normalizar_fecha(valor):
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    return None


def estuvo_activo_en_periodo_memoria(
    memoria_version,
    fecha_alta,
    fecha_baja=None
):
    fecha_alta = _normalizar_fecha(fecha_alta)
    fecha_baja = _normalizar_fecha(fecha_baja)

    if fecha_alta is None:
        return False

    memoria = getattr(memoria_version, "memoria", None)
    if memoria is None:
        return True

    periodo_inicio = getattr(memoria, "periodo_inicio", None)
    periodo_fin = getattr(memoria, "periodo_fin", None)

    if periodo_inicio is None or periodo_fin is None:
        return True

    return fecha_alta <= periodo_fin and (
        fecha_baja is None or fecha_baja >= periodo_inicio
    )


# Alias temporal para acompanar la migracion del dominio.
validar_fecha_ingreso_grupo = validar_fecha_alta_grupo


def fin_vigencia(entidad):
    """La vigencia termina en el primero de los limites funcional y logico."""
    fechas = [_normalizar_fecha(getattr(entidad, campo, None))
              for campo in ("fecha_fin", "deleted_at")]
    return min((fecha for fecha in fechas if fecha is not None), default=None)


def consultar_entidades_memoria(modelo, memoria_version, campo_grupo="grupo_utn_id", relacion=None):
    memoria = getattr(memoria_version, "memoria", None)
    grupo_id = getattr(memoria, "grupo_utn_id", None)
    filtros = []
    if memoria is None or grupo_id is None:
        raise ValidationError("Debe asociar la version de memoria a una UCT antes de generar su contenido")
    if grupo_id is not None:
        if relacion:
            # Relacion escalar: el grupo pertenece al investigador o proyecto.
            atributo = getattr(modelo, relacion)
            modelo_relacion = atributo.property.mapper.class_
            filtros.append(atributo.has(getattr(modelo_relacion, campo_grupo) == grupo_id))
        else:
            filtros.append(getattr(modelo, campo_grupo) == grupo_id)
    return modelo.query.filter(*filtros).all()


def registro_puntual_en_memoria(memoria_version, entidad, fecha):
    # Una baja posterior no borra un hecho historico. Una baja anterior al
    # periodo, o anterior al propio hecho, impide su inclusion.
    if not esta_en_periodo_memoria(memoria_version, fecha):
        return False
    baja = _normalizar_fecha(getattr(entidad, "deleted_at", None))
    inicio = getattr(getattr(memoria_version, "memoria", None), "periodo_inicio", None)
    return baja is None or ((inicio is None or baja >= inicio) and baja >= fecha)


def resolver_horas_al_fin(entidad, memoria_version):
    fin = getattr(getattr(memoria_version, "memoria", None), "periodo_fin", None)
    if fin is None:
        # Compatibilidad de pruebas aisladas sin una memoria persistida.
        activo = next((h for h in getattr(entidad, "historial_horas", []) if h.fecha_fin is None), None)
        return activo.horas_semanales if activo else getattr(entidad, "horas_semanales", None)
    candidatos = [h for h in getattr(entidad, "historial_horas", [])
                  if _normalizar_fecha(h.fecha_inicio) is not None
                  and _normalizar_fecha(h.fecha_inicio) <= fin
                  and (h.fecha_fin is None or _normalizar_fecha(h.fecha_fin) >= fin)]
    if not candidatos:
        # No completar una foto antigua desde las horas actuales.
        return None
    historial = max(candidatos, key=lambda h: (_normalizar_fecha(h.fecha_inicio), h.id or 0))
    return historial.horas_semanales


def relacion_vigente_en_memoria(memoria_version, entidad):
    # Las relaciones sin fechas funcionales no se fechan desde created_at,
    # porque admiten carga retrospectiva. Solo se descartan bajas previas.
    inicio = getattr(getattr(memoria_version, "memoria", None), "periodo_inicio", None)
    baja = _normalizar_fecha(getattr(entidad, "deleted_at", None))
    return baja is None or (inicio is not None and baja >= inicio)
