from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria,
)
import builtins
from datetime import datetime, date
from sqlalchemy import select

from modules.recursos.models.equipamiento import Equipamiento, EquipamientoMemoriaVersion
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.memorias.services.memoria_periodo_service import estuvo_activo_en_periodo_memoria
from extension import db
from modules.shared.services.text_validation import has_letter
from modules.shared.exceptions import NotFoundError, ValidationError as ValueError


class EquipamientoService:

    # ==========================================
    # HELPERS
    # ==========================================

    @staticmethod
    def _tiene_movimiento(equipamiento_id: int) -> bool:
        from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
        return db.session.scalar(select(MovimientoFinanciero.id).where(
            MovimientoFinanciero.equipamiento_id == equipamiento_id
        )) is not None

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValueError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or valor <= 0:
            raise ValueError("No pudimos procesar la solicitud. Intente nuevamente.")
        return valor

    @staticmethod
    def _validar_texto(valor: str, campo: str):
        if not isinstance(valor, str) or not valor.strip():
            label = "la denominación" if campo == "denominacion" else "la descripción"
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label} del equipamiento."}})
        if campo.casefold() in {"denominacion", "la denominacion"} and not has_letter(valor):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"denominacion": "La denominación debe contener letras."}})
        return valor.strip()

    @staticmethod
    def _validar_monto(monto):
        try:
            monto = float(monto)
        except (TypeError, builtins.ValueError):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"monto_invertido": "Ingrese un monto numérico válido."}})

        if monto <= 0:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"monto_invertido": "Ingrese un monto mayor que cero."}})

        return monto

    @staticmethod
    def _validar_fecha(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, builtins.ValueError):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_incorporacion": "Ingrese una fecha válida."}})

        if fecha > date.today():
            raise ValueError("La fecha de incorporación no puede ser futura. Revise el dato e intente nuevamente.", details={"fields": {"fecha_incorporacion": "Ingrese una fecha que no sea futura."}})

        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValueError("La fecha de incorporación debe ser posterior al 01/01/2010. Revise el dato e intente nuevamente.", details={"fields": {"fecha_incorporacion": "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

    @staticmethod
    def _validar_grupo(grupo_id):
        grupo_id = EquipamientoService._validar_id(grupo_id, "grupo_utn_id")
        grupo = db.session.get(GrupoInvestigacionUtn, grupo_id)
        if not grupo or grupo.deleted_at is not None:
            raise ValueError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")
        return grupo.id

    @staticmethod
    def _get_activo_or_404(equipamiento_id: int):
        equipamiento = db.session.get(
            Equipamiento,
            EquipamientoService._validar_id(equipamiento_id, "equipamiento_id")
        )
        if not equipamiento or equipamiento.deleted_at is not None:
            raise NotFoundError("Equipamiento no encontrado")
        return equipamiento

    # ==========================================
    # GET ALL
    # ==========================================

    @staticmethod
    def _list_query(activos: str = "true", orden: str = "asc"):
        query = Equipamiento.query

        if activos == "true":
            query = query.filter(Equipamiento.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(Equipamiento.deleted_at.isnot(None))
        elif activos == "all":
            pass
        else:
            query = query.filter(Equipamiento.deleted_at.is_(None))

        id_ = Equipamiento.id.desc() if orden == "desc" else Equipamiento.id.asc()
        return query.order_by(id_)

    @staticmethod
    def get_all(activos: str = "true"):
        return [e.serialize() for e in EquipamientoService._list_query(activos).all()]

    @staticmethod
    def get_page(page: int, per_page: int, activos="true", orden="asc"):
        from sqlalchemy.orm import selectinload
        query = EquipamientoService._list_query(activos, orden).options(
            selectinload(Equipamiento.grupo_utn)
        )
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [e.serialize() for e in rows], total

    # ==========================================
    # GET BY ID
    # ==========================================

    @staticmethod
    def get_by_id(equipamiento_id: int):
        equipamiento = db.session.get(
            Equipamiento,
            EquipamientoService._validar_id(equipamiento_id, "equipamiento_id")
        )
        if not equipamiento:
            raise NotFoundError("Equipamiento no encontrado")
        return equipamiento.serialize()

    @staticmethod
    def get_historial(equipamiento_id: int):
        equipamiento = db.session.get(
            Equipamiento,
            EquipamientoService._validar_id(equipamiento_id, "equipamiento_id")
        )
        if not equipamiento:
            raise NotFoundError("Equipamiento no encontrado")
        return AuditoriaService.obtener_historial_entidad(
            entidad="equipamiento_grupo",
            registro_id=equipamiento.id
        )

    # ==========================================
    # CREATE
    # ==========================================

    @staticmethod
    def create(data: dict, user_id: int):
        EquipamientoService._validar_payload(data)
        EquipamientoService._validar_id(user_id, "user_id")

        equipamiento = Equipamiento(
            denominacion=EquipamientoService._validar_texto(
                data.get("denominacion"), "La denominacion"
            ),
            descripcion_breve=EquipamientoService._validar_texto(
                data.get("descripcion_breve"), "La descripcion"
            ),
            fecha_incorporacion=EquipamientoService._validar_fecha(
                data.get("fecha_incorporacion")
            ),
            monto_invertido=EquipamientoService._validar_monto(
                data.get("monto_invertido")
            ),
            grupo_utn_id=EquipamientoService._validar_grupo(
                data.get("grupo_utn_id")
            ),
            created_by=user_id
        )

        db.session.add(equipamiento)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return equipamiento.serialize()

    # ==========================================
    # UPDATE
    # ==========================================

    @staticmethod
    def update(equipamiento_id: int, data: dict, user_id: int):
        EquipamientoService._validar_payload(data)
        EquipamientoService._validar_id(user_id, "user_id")
        equipamiento = EquipamientoService._get_activo_or_404(equipamiento_id)
        cambios = {}

        if "denominacion" in data:
            nuevo_valor = EquipamientoService._validar_texto(
                data["denominacion"], "La denominacion"
            )
            cambio = AuditoriaService.construir_cambio(
                equipamiento.denominacion,
                nuevo_valor
            )
            if cambio:
                cambios["denominacion"] = cambio
                equipamiento.denominacion = nuevo_valor

        if "descripcion_breve" in data:
            nuevo_valor = EquipamientoService._validar_texto(
                data["descripcion_breve"], "La descripcion"
            )
            cambio = AuditoriaService.construir_cambio(
                equipamiento.descripcion_breve,
                nuevo_valor
            )
            if cambio:
                cambios["descripcion_breve"] = cambio
                equipamiento.descripcion_breve = nuevo_valor

        if "monto_invertido" in data:
            nuevo_valor = EquipamientoService._validar_monto(
                data["monto_invertido"]
            )
            cambio = AuditoriaService.construir_cambio(
                equipamiento.monto_invertido,
                nuevo_valor
            )
            if cambio:
                cambios["monto_invertido"] = cambio
                equipamiento.monto_invertido = nuevo_valor

        if "fecha_incorporacion" in data:
            nuevo_valor = EquipamientoService._validar_fecha(
                data["fecha_incorporacion"]
            )
            cambio = AuditoriaService.construir_cambio(
                equipamiento.fecha_incorporacion,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_incorporacion"] = cambio
                equipamiento.fecha_incorporacion = nuevo_valor

        if "grupo_utn_id" in data:
            nuevo_valor = EquipamientoService._validar_grupo(
                data["grupo_utn_id"]
            )
            if nuevo_valor != equipamiento.grupo_utn_id and EquipamientoService._tiene_movimiento(equipamiento.id):
                raise ValueError("No se puede cambiar el grupo de un equipamiento vinculado a un movimiento.")
            cambio = AuditoriaService.construir_cambio(
                equipamiento.grupo_utn_id,
                nuevo_valor
            )
            if cambio:
                cambios["grupo_utn_id"] = cambio
                equipamiento.grupo_utn_id = nuevo_valor

        if cambios:
            equipamiento.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="equipamiento_grupo",
                registro_id=equipamiento.id,
                cambios=cambios,
                user_id=user_id
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return equipamiento.serialize()

    # ==========================================
    # SOFT DELETE
    # ==========================================

    @staticmethod
    def delete(equipamiento_id: int, user_id: int):
        EquipamientoService._validar_id(user_id, "user_id")
        equipamiento = EquipamientoService._get_activo_or_404(equipamiento_id)

        equipamiento.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Equipamiento eliminado correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        equipamientos = consultar_entidades_memoria(Equipamiento, memoria_version)

        snapshots = []
        for equipamiento in equipamientos:
            if not estuvo_activo_en_periodo_memoria(
                memoria_version,
                equipamiento.fecha_incorporacion,
                getattr(equipamiento, "deleted_at", None)
            ):
                continue
            snapshot = EquipamientoMemoriaVersion(
                memoria_version_id=memoria_version.id,
                equipamiento_id=equipamiento.id,
                denominacion=equipamiento.denominacion,
                descripcion_breve=equipamiento.descripcion_breve,
                fecha_incorporacion=equipamiento.fecha_incorporacion,
                monto_invertido=equipamiento.monto_invertido,
                grupo_utn_id=equipamiento.grupo_utn_id,
                grupo_utn_nombre=(
                    equipamiento.grupo_utn.nombre_sigla_grupo
                    if equipamiento.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            EquipamientoMemoriaVersion.query
            .filter(
                EquipamientoMemoriaVersion.memoria_version_id == memoria_version_id,
                EquipamientoMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(EquipamientoMemoriaVersion.denominacion.asc())
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
