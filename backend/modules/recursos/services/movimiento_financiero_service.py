"""Operaciones de dominio para los movimientos financieros del grupo."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from extension import db
from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.models.movimiento_financiero import (
    CategoriaErogacion, MovimientoFinanciero, MovimientoMemoriaVersion,
    validar_monto_financiero,
)
from modules.recursos.services.saldo_financiero_service import SaldoFinancieroService
from modules.recursos.services.tipo_cambio_service import TipoCambioService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date


class MovimientoFinancieroService:
    _CAMPOS_ALTA = frozenset({
        "grupo_utn_id", "fecha", "tipo_movimiento", "monto", "moneda",
        "fuente_financiamiento_id", "categoria_erogacion_id",
        "equipamiento_id",
    })
    _CAMPOS_EDICION = frozenset({
        "fecha", "monto", "fuente_financiamiento_id", "categoria_erogacion_id",
        "equipamiento_id",
    })

    @staticmethod
    def _id_positivo(value, field):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError(
                "Revise los campos indicados e intente nuevamente.",
                details={"fields": {field: "Seleccione un valor válido."}},
            )
        return value

    @staticmethod
    def _fecha(value):
        try:
            fecha = datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError(
                "Revise los campos indicados e intente nuevamente.",
                details={"fields": {"fecha": "Ingrese una fecha válida."}},
            ) from None
        validate_institutional_date(fecha, allow_future=False)
        return fecha

    @staticmethod
    def _bloquear_grupo(grupo_id: int):
        grupo = db.session.execute(
            select(GrupoInvestigacionUtn.id)
            .where(
                GrupoInvestigacionUtn.id == grupo_id,
                GrupoInvestigacionUtn.deleted_at.is_(None),
            )
            .with_for_update()
        ).scalar_one_or_none()
        if grupo is None:
            raise NotFoundError(
                "El grupo ya no está disponible. Recargue el formulario e intente nuevamente."
            )

    @staticmethod
    def _equipamiento_disponible(equipamiento_id: int, grupo_id: int, movimiento_id: int | None = None):
        equipo = db.session.get(Equipamiento, MovimientoFinancieroService._id_positivo(
            equipamiento_id, "equipamiento_id"
        ))
        if not equipo or equipo.deleted_at is not None or equipo.grupo_utn_id != grupo_id:
            raise NotFoundError("El equipamiento no está disponible para este grupo.")
        vinculado = db.session.scalar(select(MovimientoFinanciero.id).where(
            MovimientoFinanciero.equipamiento_id == equipo.id,
            MovimientoFinanciero.id != movimiento_id if movimiento_id is not None else True,
        ))
        if vinculado is not None:
            raise ConflictError(
                "El equipamiento ya está vinculado a otro egreso.",
                details={"fields": {"equipamiento_id": "Seleccione otro equipamiento."}},
            )
        return equipo

    @staticmethod
    def _monto_equipo(equipo: Equipamiento) -> Decimal:
        return validar_monto_financiero(
            Decimal(str(equipo.monto_invertido)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

    @staticmethod
    def _list_query(filters: dict | None = None):
        filters = filters or {}
        query = select(MovimientoFinanciero).options(
            joinedload(MovimientoFinanciero.grupo_utn),
            joinedload(MovimientoFinanciero.fuente_financiamiento),
            joinedload(MovimientoFinanciero.categoria_erogacion),
            joinedload(MovimientoFinanciero.equipamiento),
        )
        activos = filters.get("activos", "true")
        if activos == "true":
            query = query.where(MovimientoFinanciero.deleted_at.is_(None))
        elif activos == "false":
            query = query.where(MovimientoFinanciero.deleted_at.is_not(None))
        elif activos != "all":
            raise ValidationError("El filtro de estado no es válido.")
        if filters.get("grupo_utn_id"):
            try:
                parsed_grupo_id = int(filters["grupo_utn_id"])
            except (TypeError, ValueError):
                raise ValidationError("El grupo indicado no es válido.") from None
            grupo_id = MovimientoFinancieroService._id_positivo(
                parsed_grupo_id, "grupo_utn_id"
            )
            query = query.where(MovimientoFinanciero.grupo_utn_id == grupo_id)
        query = query.order_by(
            MovimientoFinanciero.fecha.desc(),
            MovimientoFinanciero.numero_movimiento.desc(),
        )
        return query

    @staticmethod
    def get_all(filters: dict | None = None):
        query = MovimientoFinancieroService._list_query(filters)
        return [item.serialize() for item in db.session.scalars(query).unique().all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = MovimientoFinancieroService._list_query(filters)
        total = db.session.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        rows = db.session.scalars(
            query.offset((page - 1) * per_page).limit(per_page)
        ).unique().all()
        return [item.serialize() for item in rows], total

    @staticmethod
    def get_by_id(movimiento_id: int):
        MovimientoFinancieroService._id_positivo(movimiento_id, "id")
        movimiento = db.session.get(MovimientoFinanciero, movimiento_id)
        if not movimiento:
            raise NotFoundError("Movimiento no encontrado.")
        return movimiento.serialize()

    @staticmethod
    def get_historial(movimiento_id: int):
        MovimientoFinancieroService.get_by_id(movimiento_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="movimiento_financiero", registro_id=movimiento_id,
        )

    @staticmethod
    def equipamientos_disponibles(grupo_id: int, movimiento_id: int | None = None,
                                  page: int | None = None, per_page: int | None = None):
        MovimientoFinancieroService._id_positivo(grupo_id, "grupo_utn_id")
        if movimiento_id is not None:
            MovimientoFinancieroService._id_positivo(movimiento_id, "movimiento_id")
        grupo = db.session.get(GrupoInvestigacionUtn, grupo_id)
        if not grupo or grupo.deleted_at is not None:
            raise NotFoundError("El grupo no está disponible.")
        usado = select(MovimientoFinanciero.id).where(
            MovimientoFinanciero.equipamiento_id == Equipamiento.id,
            MovimientoFinanciero.id != movimiento_id if movimiento_id is not None else True,
        ).exists()
        query = select(Equipamiento).where(
            Equipamiento.grupo_utn_id == grupo_id,
            Equipamiento.deleted_at.is_(None),
            ~usado,
        ).order_by(Equipamiento.denominacion.asc(), Equipamiento.id.asc())
        total = db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) if page is not None else None
        if page is not None:
            query = query.offset((page - 1) * per_page).limit(per_page)
        equipos = db.session.scalars(query).unique().all()
        data = [{
            "id": equipo.id,
            "denominacion": equipo.denominacion,
            "monto_invertido": str(MovimientoFinancieroService._monto_equipo(equipo)),
        } for equipo in equipos]
        return (data, total) if page is not None else data

    @staticmethod
    def create(data: dict, user_id: int):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Envíe los datos del movimiento e intente nuevamente.")
        if data.keys() - MovimientoFinancieroService._CAMPOS_ALTA:
            raise ValidationError("El movimiento contiene campos que no se pueden cargar.")

        grupo_id = MovimientoFinancieroService._id_positivo(
            data.get("grupo_utn_id"), "grupo_utn_id"
        )
        tipo = data.get("tipo_movimiento")
        if tipo not in {"INGRESO", "EGRESO"}:
            raise ValidationError(
                "Revise los campos indicados e intente nuevamente.",
                details={"fields": {"tipo_movimiento": "Seleccione ingreso o egreso."}},
            )
        fecha = MovimientoFinancieroService._fecha(data.get("fecha"))
        moneda = data.get("moneda")
        if moneda not in {"ARS", "USD"}:
            raise ValidationError("Seleccione una moneda válida.",
                                  details={"fields": {"moneda": "Seleccione ARS o USD."}})
        # Serializa la numeración, el saldo y la unicidad del equipo dentro del grupo.
        MovimientoFinancieroService._bloquear_grupo(grupo_id)
        equipo = None
        if data.get("equipamiento_id") is not None:
            if moneda != "ARS":
                raise ValidationError("El equipamiento utiliza un monto en ARS. Seleccione ARS o quite el vínculo.",
                                      details={"fields": {"moneda": "Seleccione ARS para vincular equipamiento."}})
            if tipo != "EGRESO":
                raise ValidationError("Un ingreso no puede incluir equipamiento.")
            equipo = MovimientoFinancieroService._equipamiento_disponible(
                data["equipamiento_id"], grupo_id
            )
        # El monto del equipamiento se toma solo al vincularlo; luego queda como snapshot.
        movimiento = MovimientoFinanciero(
            grupo_utn_id=grupo_id,
            tipo_movimiento=tipo,
            monto=MovimientoFinancieroService._monto_equipo(equipo) if equipo else data.get("monto"),
            moneda=moneda,
            fecha=fecha,
            created_by=user_id,
            equipamiento_id=equipo.id if equipo else None,
        )

        fuente_id = data.get("fuente_financiamiento_id")
        categoria_id = data.get("categoria_erogacion_id")
        fuente_id = MovimientoFinancieroService._id_positivo(
            fuente_id, "fuente_financiamiento_id"
        )
        fuente = db.session.get(FuenteFinanciamiento, fuente_id)
        if not fuente or fuente.deleted_at is not None:
            raise NotFoundError("La fuente ya no está disponible. Elija otra e intente nuevamente.")
        movimiento.fuente_financiamiento_id = fuente.id
        if moneda == "USD":
            cotizacion = TipoCambioService.obtener_vigente_para_fecha(fecha)
            movimiento.tipo_cambio = cotizacion
            movimiento.tipo_cambio_aplicado = cotizacion.valor
            movimiento.monto_equivalente_ars = (
                movimiento.monto * cotizacion.valor
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            movimiento.monto_equivalente_ars = movimiento.monto
        if tipo == "INGRESO":
            if categoria_id is not None:
                raise ValidationError(
                    "Un ingreso no debe incluir una categoría de erogación.",
                    details={"fields": {"categoria_erogacion_id": "Quite la categoría."}},
                )
        else:
            categoria_id = MovimientoFinancieroService._id_positivo(
                categoria_id, "categoria_erogacion_id"
            )
            categoria = db.session.get(CategoriaErogacion, categoria_id)
            if not categoria or categoria.deleted_at is not None:
                raise NotFoundError("La categoría ya no está disponible. Elija otra e intente nuevamente.")
            movimiento.categoria_erogacion_id = categoria.id

        if tipo == "EGRESO":
            saldo = SaldoFinancieroService.calcular(grupo_id).saldo_disponible
            saldo_fuente = SaldoFinancieroService.saldo_de_fuente(grupo_id, fuente_id)
            if movimiento.monto_equivalente_ars > saldo or movimiento.monto_equivalente_ars > saldo_fuente:
                raise ConflictError(
                    "El saldo disponible de la fuente no alcanza para registrar el egreso.",
                    details={"fields": {"monto": "Ingrese un monto igual o menor al saldo disponible de la fuente."}},
                )

        ultimo = db.session.scalar(
            select(func.max(MovimientoFinanciero.numero_movimiento)).where(
                MovimientoFinanciero.grupo_utn_id == grupo_id
            )
        )
        movimiento.numero_movimiento = (ultimo or 0) + 1
        db.session.add(movimiento)
        db.session.commit()
        return movimiento.serialize()

    @staticmethod
    def update(movimiento_id: int, data: dict, user_id: int):
        MovimientoFinancieroService._id_positivo(movimiento_id, "id")
        if not isinstance(data, dict) or not data:
            raise ValidationError("Envíe los cambios del movimiento e intente nuevamente.")
        if data.keys() - MovimientoFinancieroService._CAMPOS_EDICION:
            raise ValidationError(
                "El tipo, la moneda, el grupo y el número de movimiento no pueden modificarse."
            )
        movimiento = db.session.get(MovimientoFinanciero, movimiento_id)
        if not movimiento or movimiento.deleted_at is not None:
            raise NotFoundError("Movimiento no encontrado.")
        MovimientoFinancieroService._bloquear_grupo(movimiento.grupo_utn_id)
        db.session.refresh(movimiento)
        if movimiento.deleted_at is not None:
            raise NotFoundError("Movimiento no encontrado.")

        nuevos = {}
        if "fecha" in data:
            nuevos["fecha"] = MovimientoFinancieroService._fecha(data["fecha"])
            if movimiento.moneda == "USD" and nuevos["fecha"] != movimiento.fecha:
                raise ValidationError("La fecha de un movimiento USD no puede cambiar porque conserva su cotización histórica.")
        if "monto" in data:
            nuevos["monto"] = validar_monto_financiero(data["monto"])
        if "fuente_financiamiento_id" in data:
            fuente_id = MovimientoFinancieroService._id_positivo(
                data["fuente_financiamiento_id"], "fuente_financiamiento_id"
            )
            fuente = db.session.get(FuenteFinanciamiento, fuente_id)
            if not fuente or fuente.deleted_at is not None:
                raise NotFoundError("La fuente ya no está disponible. Elija otra e intente nuevamente.")
            nuevos["fuente_financiamiento_id"] = fuente.id
        if "equipamiento_id" in data:
            if movimiento.tipo_movimiento != "EGRESO":
                raise ValidationError("Un ingreso no puede incluir equipamiento.")
            if data["equipamiento_id"] is None:
                nuevos["equipamiento_id"] = None
            else:
                equipo = MovimientoFinancieroService._equipamiento_disponible(
                    data["equipamiento_id"], movimiento.grupo_utn_id, movimiento.id
                )
                nuevos["equipamiento_id"] = equipo.id
                if equipo.id != movimiento.equipamiento_id:
                    nuevos["monto"] = MovimientoFinancieroService._monto_equipo(equipo)
        if "monto" in data and movimiento.equipamiento_id is not None and (
            "equipamiento_id" not in data or nuevos["equipamiento_id"] == movimiento.equipamiento_id
        ) and validar_monto_financiero(data["monto"]) != movimiento.monto:
            raise ValidationError("Desvincule el equipamiento antes de modificar el monto.")
        if "categoria_erogacion_id" in data:
            if movimiento.tipo_movimiento != "EGRESO":
                raise ValidationError("Un ingreso no puede tener categoría de erogación.")
            categoria_id = MovimientoFinancieroService._id_positivo(
                data["categoria_erogacion_id"], "categoria_erogacion_id"
            )
            categoria = db.session.get(CategoriaErogacion, categoria_id)
            if not categoria or categoria.deleted_at is not None:
                raise NotFoundError("La categoría ya no está disponible. Elija otra e intente nuevamente.")
            nuevos["categoria_erogacion_id"] = categoria.id

        nuevo_monto = nuevos.get("monto", movimiento.monto)
        nuevo_equivalente = (nuevo_monto * movimiento.tipo_cambio_aplicado).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if movimiento.moneda == "USD" else nuevo_monto
        anterior_equivalente = movimiento.monto_equivalente_ars or movimiento.monto
        nueva_fuente = nuevos.get("fuente_financiamiento_id", movimiento.fuente_financiamiento_id)
        signo = 1 if movimiento.tipo_movimiento == "INGRESO" else -1
        saldo_fuente_anterior = SaldoFinancieroService.saldo_de_fuente(
            movimiento.grupo_utn_id, movimiento.fuente_financiamiento_id
        )
        if nueva_fuente == movimiento.fuente_financiamiento_id:
            saldo_fuente_resultante = saldo_fuente_anterior + signo * (nuevo_equivalente - anterior_equivalente)
        else:
            saldo_fuente_resultante = saldo_fuente_anterior - signo * anterior_equivalente
            saldo_fuente_nueva = SaldoFinancieroService.saldo_de_fuente(
                movimiento.grupo_utn_id, nueva_fuente
            ) + signo * nuevo_equivalente
            if saldo_fuente_nueva < 0:
                raise ConflictError("El saldo disponible de la nueva fuente es insuficiente.",
                                    details={"fields": {"monto": "El monto supera el saldo de la fuente."}})
        if saldo_fuente_resultante < 0:
            raise ConflictError("El cambio dejaría a la fuente sin saldo suficiente.",
                                details={"fields": {"monto": "El monto supera el saldo de la fuente."}})
        if nuevo_monto != movimiento.monto:
            saldo = SaldoFinancieroService.calcular(movimiento.grupo_utn_id).saldo_disponible
            if movimiento.tipo_movimiento == "EGRESO":
                saldo_resultante = saldo + anterior_equivalente - nuevo_equivalente
            else:
                saldo_resultante = saldo - anterior_equivalente + nuevo_equivalente
            if saldo_resultante < 0:
                raise ConflictError(
                    "El cambio dejaría al grupo sin saldo suficiente.",
                    details={"fields": {"monto": "El monto supera el saldo disponible."}},
                )

        cambios = {}
        for campo, nuevo_valor in nuevos.items():
            anterior = getattr(movimiento, campo)
            cambio = AuditoriaService.construir_cambio(
                str(anterior) if campo == "monto" else anterior,
                str(nuevo_valor) if campo == "monto" else nuevo_valor,
            )
            if cambio:
                cambios[campo] = cambio
                setattr(movimiento, campo, nuevo_valor)
        if cambios:
            if nuevo_equivalente != anterior_equivalente:
                cambios["monto_equivalente_ars"] = AuditoriaService.construir_cambio(
                    str(anterior_equivalente), str(nuevo_equivalente)
                )
                movimiento.monto_equivalente_ars = nuevo_equivalente
            movimiento.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="movimiento_financiero", registro_id=movimiento.id,
                cambios=cambios, user_id=user_id,
            )
            db.session.commit()
        return movimiento.serialize()

    @staticmethod
    def delete(movimiento_id: int, user_id: int):
        MovimientoFinancieroService._id_positivo(movimiento_id, "id")
        movimiento = db.session.get(MovimientoFinanciero, movimiento_id)
        if not movimiento or movimiento.deleted_at is not None:
            raise NotFoundError("Movimiento no encontrado.")
        MovimientoFinancieroService._bloquear_grupo(movimiento.grupo_utn_id)
        db.session.refresh(movimiento)
        if movimiento.deleted_at is not None:
            raise NotFoundError("Movimiento no encontrado.")
        if movimiento.tipo_movimiento == "INGRESO":
            saldo = SaldoFinancieroService.calcular(movimiento.grupo_utn_id).saldo_disponible
            saldo_fuente = SaldoFinancieroService.saldo_de_fuente(
                movimiento.grupo_utn_id, movimiento.fuente_financiamiento_id
            )
            equivalente = movimiento.monto_equivalente_ars or movimiento.monto
            if saldo - equivalente < 0 or saldo_fuente - equivalente < 0:
                raise ConflictError(
                    "No se puede eliminar el ingreso porque el saldo resultante sería negativo."
                )
        movimiento.soft_delete(user_id)
        db.session.commit()
        return {"message": "Movimiento eliminado correctamente."}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id: int):
        movimientos = consultar_entidades_memoria(MovimientoFinanciero, memoria_version)
        snapshots = []
        for movimiento in movimientos:
            if not registro_puntual_en_memoria(
                memoria_version, movimiento, movimiento.fecha,
            ):
                continue
            snapshot = MovimientoMemoriaVersion(
                memoria_version_id=memoria_version.id,
                movimiento_id=movimiento.id,
                numero_movimiento=movimiento.numero_movimiento,
                fecha=movimiento.fecha,
                tipo_movimiento=movimiento.tipo_movimiento,
                monto=movimiento.monto,
                moneda=movimiento.moneda,
                tipo_cambio_aplicado=movimiento.tipo_cambio_aplicado,
                monto_equivalente_ars=movimiento.monto_equivalente_ars,
                fecha_cotizacion=(movimiento.tipo_cambio.fecha_cotizacion if movimiento.tipo_cambio else None),
                serie_bcra=(movimiento.tipo_cambio.serie_bcra if movimiento.tipo_cambio else None),
                fuente_financiamiento_id=movimiento.fuente_financiamiento_id,
                fuente_financiamiento_nombre=(
                    movimiento.fuente_financiamiento.nombre
                    if movimiento.fuente_financiamiento else None
                ),
                categoria_erogacion_id=movimiento.categoria_erogacion_id,
                categoria_erogacion_codigo=(
                    movimiento.categoria_erogacion.codigo
                    if movimiento.categoria_erogacion else None
                ),
                categoria_erogacion_nombre=(
                    movimiento.categoria_erogacion.nombre
                    if movimiento.categoria_erogacion else None
                ),
                equipamiento_id=movimiento.equipamiento_id,
                equipamiento_denominacion=(
                    movimiento.equipamiento.denominacion if movimiento.equipamiento else None
                ),
                grupo_utn_id=movimiento.grupo_utn_id,
                grupo_utn_nombre=(
                    movimiento.grupo_utn.nombre_sigla_grupo
                    if movimiento.grupo_utn else None
                ),
                created_by=user_id,
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)
        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = MovimientoMemoriaVersion.query.filter(
            MovimientoMemoriaVersion.memoria_version_id == memoria_version_id,
            MovimientoMemoriaVersion.deleted_at.is_(None),
        ).order_by(
            MovimientoMemoriaVersion.fecha.desc(),
            MovimientoMemoriaVersion.numero_movimiento.desc(),
        ).all()
        return [snapshot.serialize() for snapshot in snapshots]
