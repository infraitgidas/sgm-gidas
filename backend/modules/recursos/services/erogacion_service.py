from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from datetime import date, datetime
import math

from modules.recursos.models.erogacion import Erogacion, TipoErogacion, ErogacionMemoriaVersion
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError


class ErogacionService:

    @staticmethod
    def _get_activa_or_404(erogacion_id: int):
        erogacion = db.session.get(Erogacion, erogacion_id)
        if not erogacion or erogacion.deleted_at is not None:
            raise NotFoundError("Erogacion no encontrada")
        return erogacion

    @staticmethod
    def get_all(filters: dict = None):
        query = Erogacion.query

        if not filters:
            filters = {"activos": "true"}

        activos = (filters.get("activos", "true") or "true").strip().lower()

        if activos == "true":
            query = query.filter(Erogacion.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(Erogacion.deleted_at.isnot(None))

        if filters.get("fuente_financiamiento_id"):
            query = query.filter(
                Erogacion.fuente_financiamiento_id == filters["fuente_financiamiento_id"]
            )

        if filters.get("tipo_erogacion_id"):
            query = query.filter(
                Erogacion.tipo_erogacion_id == filters["tipo_erogacion_id"]
            )

        orden = filters.get("orden")
        if orden == "asc":
            query = query.order_by(Erogacion.fecha.asc())
        else:
            query = query.order_by(Erogacion.fecha.desc())

        return [e.serialize() for e in query.all()]

    @staticmethod
    def get_by_id(erogacion_id: int):
        erogacion = db.session.get(Erogacion, erogacion_id)
        if not erogacion:
            raise NotFoundError("Erogacion no encontrada")
        return erogacion.serialize()

    @staticmethod
    def get_historial(erogacion_id: int):
        erogacion = db.session.get(Erogacion, erogacion_id)
        if not erogacion:
            raise NotFoundError("Erogacion no encontrada")
        return AuditoriaService.obtener_historial_entidad(
            entidad="erogacion",
            registro_id=erogacion.id
        )


    @staticmethod
    def vaLidar_numero_erogacion(numero, grupo_id, erogacion_id=None):
        if isinstance(numero, bool) or (isinstance(numero, float) and not numero.is_integer()) or (isinstance(numero, str) and not numero.strip().isdigit()):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"numero_erogacion": "Ingrese un número entero positivo."}})
        try:
            numero_int = int(numero)
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"numero_erogacion": "Ingrese un número entero positivo."}})
        if numero_int <= 0:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"numero_erogacion": "Ingrese un número entero positivo."}})
        query = Erogacion.query.filter(
            Erogacion.numero_erogacion == numero_int,
            Erogacion.grupo_utn_id == grupo_id,
            Erogacion.deleted_at.is_(None)
        )
        if erogacion_id:
            query = query.filter(Erogacion.id != erogacion_id)

        existe = query.first()
        if existe:
            raise ConflictError("Ya existe una erogación con ese número. Ingrese otro e intente nuevamente.", details={"fields": {"numero_erogacion": "Ingrese un número que no esté en uso."}})
        return numero_int

    @staticmethod
    def _validar_monto(valor, campo):
        try:
            monto = float(valor)
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese un monto numérico válido."}})
        if not math.isfinite(monto) or monto < 0:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese un monto mayor o igual a cero."}})
        return monto

    @staticmethod
    def _validar_fecha(valor):
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha": "Ingrese una fecha válida."}})
        if fecha < INSTITUTIONAL_MIN_DATE or fecha > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha": "Ingrese una fecha desde el 01/01/2010 que no sea futura."}})
        return fecha
        
    @staticmethod
    def create(data: dict, user_id: int):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Envíe los datos de la erogación e intente nuevamente.")

        numero = ErogacionService.vaLidar_numero_erogacion(data.get("numero_erogacion"), data.get("grupo_utn_id"))
        grupo_id = data.get("grupo_utn_id")

        if not grupo_id:
            raise ValidationError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

        grupo = db.session.get(GrupoInvestigacionUtn, grupo_id)
        if not grupo or grupo.deleted_at is not None:
            raise NotFoundError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

        existe = Erogacion.query.filter(
            Erogacion.numero_erogacion == numero,
            Erogacion.grupo_utn_id == grupo_id,
            Erogacion.deleted_at.is_(None)
        ).first()
        if existe:
            raise ConflictError("Ya existe una erogación con ese número. Ingrese otro e intente nuevamente.", details={"fields": {"numero_erogacion": "Ingrese un número que no esté en uso."}})

        egresos = ErogacionService._validar_monto(data.get("egresos"), "egresos")
        ingresos = ErogacionService._validar_monto(data.get("ingresos"), "ingresos")
        if egresos == 0 and ingresos == 0:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"egresos": "Ingrese un monto en egresos o ingresos.", "ingresos": "Ingrese un monto en egresos o ingresos."}})

        tipo = db.session.get(TipoErogacion, data.get("tipo_erogacion_id"))
        if not tipo:
            raise NotFoundError("El tipo de erogación ya no está disponible. Elija otro e intente nuevamente.", details={"fields": {"tipo_erogacion_id": "Seleccione un tipo disponible."}})

        fuente = db.session.get(
            FuenteFinanciamiento,
            data.get("fuente_financiamiento_id")
        )
        if not fuente:
            raise NotFoundError("La fuente de financiamiento ya no está disponible. Elija otra e intente nuevamente.", details={"fields": {"fuente_financiamiento_id": "Seleccione una fuente disponible."}})

        fecha = ErogacionService._validar_fecha(data.get("fecha")) if data.get("fecha") else date.today()

        erogacion = Erogacion(
            numero_erogacion=numero,
            egresos=egresos,
            ingresos=ingresos,
            fecha=fecha,
            tipo_erogacion_id=tipo.id,
            fuente_financiamiento_id=fuente.id,
            grupo_utn_id=grupo.id,
            created_by=user_id
        )

        db.session.add(erogacion)
        db.session.commit()
        return erogacion.serialize()

    @staticmethod
    def update(erogacion_id: int, data: dict, user_id: int):
        erogacion = ErogacionService._get_activa_or_404(erogacion_id)
        if not isinstance(data, dict) or not data:
            raise ValidationError("Envíe los cambios de la erogación e intente nuevamente.")
        nuevo_egreso = ErogacionService._validar_monto(data["egresos"], "egresos") if "egresos" in data else erogacion.egresos
        nuevo_ingreso = ErogacionService._validar_monto(data["ingresos"], "ingresos") if "ingresos" in data else erogacion.ingresos
        if nuevo_egreso == 0 and nuevo_ingreso == 0:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"egresos": "Ingrese un monto en egresos o ingresos.", "ingresos": "Ingrese un monto en egresos o ingresos."}})
        nuevo_numero = (
            ErogacionService.vaLidar_numero_erogacion(
                data["numero_erogacion"], erogacion.grupo_utn_id, erogacion.id
            ) if "numero_erogacion" in data else erogacion.numero_erogacion
        )
        nueva_fecha = ErogacionService._validar_fecha(data["fecha"]) if "fecha" in data else erogacion.fecha
        nuevo_tipo_id = erogacion.tipo_erogacion_id
        if "tipo_erogacion_id" in data:
            tipo = db.session.get(TipoErogacion, data["tipo_erogacion_id"])
            if not tipo or tipo.deleted_at is not None:
                raise NotFoundError("El tipo de erogación ya no está disponible. Elija otro e intente nuevamente.", details={"fields": {"tipo_erogacion_id": "Seleccione un tipo disponible."}})
            nuevo_tipo_id = tipo.id
        nueva_fuente_id = erogacion.fuente_financiamiento_id
        if "fuente_financiamiento_id" in data:
            fuente = db.session.get(FuenteFinanciamiento, data["fuente_financiamiento_id"])
            if not fuente or fuente.deleted_at is not None:
                raise NotFoundError("La fuente de financiamiento ya no está disponible. Elija otra e intente nuevamente.", details={"fields": {"fuente_financiamiento_id": "Seleccione una fuente disponible."}})
            nueva_fuente_id = fuente.id
        cambios = {}

        for campo, nuevo_valor in (
            ("numero_erogacion", nuevo_numero),
            ("fecha", nueva_fecha),
            ("tipo_erogacion_id", nuevo_tipo_id),
            ("fuente_financiamiento_id", nueva_fuente_id),
        ):
            if campo in data:
                cambio = AuditoriaService.construir_cambio(getattr(erogacion, campo), nuevo_valor)
                if cambio:
                    cambios[campo] = cambio
                    setattr(erogacion, campo, nuevo_valor)

        if "egresos" in data:
            cambio = AuditoriaService.construir_cambio(
                erogacion.egresos,
                nuevo_egreso
            )
            if cambio:
                cambios["egresos"] = cambio
                erogacion.egresos = nuevo_egreso

        if "ingresos" in data:
            cambio = AuditoriaService.construir_cambio(
                erogacion.ingresos,
                nuevo_ingreso
            )
            if cambio:
                cambios["ingresos"] = cambio
                erogacion.ingresos = nuevo_ingreso

        if cambios:
            erogacion.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="erogacion",
                registro_id=erogacion.id,
                cambios=cambios,
                user_id=user_id
            )

        db.session.commit()
        return erogacion.serialize()

    @staticmethod
    def delete(erogacion_id: int, user_id: int):
        erogacion = ErogacionService._get_activa_or_404(erogacion_id)
        erogacion.soft_delete(user_id)
        db.session.commit()
        return {"message": "Erogacion eliminada correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        erogaciones = consultar_entidades_memoria(Erogacion, memoria_version)

        snapshots = []
        for erogacion in erogaciones:
            if not registro_puntual_en_memoria(memoria_version, erogacion, erogacion.fecha):
                continue
            snapshot = ErogacionMemoriaVersion(
                memoria_version_id=memoria_version.id,
                erogacion_id=erogacion.id,
                numero_erogacion=erogacion.numero_erogacion,
                egresos=erogacion.egresos,
                ingresos=erogacion.ingresos,
                fecha=erogacion.fecha,
                tipo_erogacion_id=erogacion.tipo_erogacion_id,
                tipo_erogacion_nombre=(
                    erogacion.tipo_erogacion.nombre
                    if erogacion.tipo_erogacion else None
                ),
                fuente_financiamiento_id=erogacion.fuente_financiamiento_id,
                fuente_financiamiento_nombre=(
                    erogacion.fuente_financiamiento.nombre
                    if erogacion.fuente_financiamiento else None
                ),
                grupo_utn_id=erogacion.grupo_utn_id,
                grupo_utn_nombre=(
                    erogacion.grupo_utn.nombre_sigla_grupo
                    if erogacion.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            ErogacionMemoriaVersion.query
            .filter(
                ErogacionMemoriaVersion.memoria_version_id == memoria_version_id,
                ErogacionMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(ErogacionMemoriaVersion.fecha.desc())
            .all()
        )
        return [snapshot.serialize() for snapshot in snapshots]
