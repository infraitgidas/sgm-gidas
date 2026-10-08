from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, fin_vigencia, relacion_vigente_en_memoria,
)
import builtins
import math
from datetime import datetime
from extension import db
from sqlalchemy import Integer, cast, func, text
from sqlalchemy.orm import joinedload, selectinload
from modules.shared.services.text_validation import has_letter, has_only_letters_and_spaces

from modules.transferencia.models.transferencia_socio import (
    Adoptante,
    TransferenciaSocioProductiva,
    TipoContrato,
    AdoptanteTransferencia,
    TransferenciaSocioProductivaMemoriaVersion,
    AdoptanteTransferenciaMemoriaVersion,
)
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.memorias.services.memoria_periodo_service import estuvo_activo_en_periodo_memoria
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError as ValueError
from modules.shared.controllers.pagination import table_query_page, table_scope_predicate


class TransferenciaSocioProductivaService:

    @staticmethod
    def _resolver_adoptantes(data):
        if "adoptantes_ids" not in data and "adoptantes_nuevos" not in data:
            return None
        ids = data.get("adoptantes_ids", [])
        nombres = data.get("adoptantes_nuevos", [])
        if not isinstance(ids, list) or not isinstance(nombres, list):
            raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "Revise los adoptantes seleccionados."}})
        if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "Seleccione adoptantes válidos sin repetir."}})
        limpios = []
        for nombre in nombres:
            if not isinstance(nombre, str) or not has_only_letters_and_spaces(nombre):
                raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "Ingrese nombres de adoptantes con letras y espacios."}})
            limpio = " ".join(nombre.split())
            if not limpio:
                raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "Ingrese el nombre del adoptante."}})
            limpios.append(limpio)
        if len({nombre.casefold() for nombre in limpios}) != len(limpios):
            raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "No repita adoptantes nuevos."}})
        existentes = db.session.query(Adoptante).filter(Adoptante.id.in_(ids), Adoptante.deleted_at.is_(None)).all() if ids else []
        if len(existentes) != len(ids):
            raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": "Un adoptante ya no está disponible. Recargue el formulario."}})
        for nombre in limpios:
            if db.session.query(Adoptante).filter(func.lower(Adoptante.nombre) == nombre.lower(), Adoptante.deleted_at.is_(None)).first():
                raise ValueError("Revise los adoptantes e intente nuevamente.", details={"fields": {"adoptantes_ids": f"{nombre} ya existe. Selecciónelo de la lista."}})
        return existentes, limpios

    @staticmethod
    def _sincronizar_adoptantes(transferencia, seleccion, user_id):
        if seleccion is None:
            return False
        existentes, nombres = seleccion
        adoptantes = list(existentes)
        for nombre in nombres:
            adoptante = Adoptante(nombre=nombre, created_by=user_id)
            db.session.add(adoptante)
            db.session.flush()
            adoptantes.append(adoptante)
        actuales = {item.adoptante_id: item for item in transferencia.participaciones if item.deleted_at is None}
        nuevos_ids = {item.id for item in adoptantes}
        hubo_cambios = False
        for adoptante_id, participacion in actuales.items():
            if adoptante_id not in nuevos_ids:
                participacion.soft_delete(user_id)
                hubo_cambios = True
                AuditoriaService.registrar_evento_relacion(
                    entidad="transferencia_socio_productiva", registro_id=transferencia.id,
                    relacion="adoptantes", accion="desvincular",
                    detalle={"adoptante_id": adoptante_id, "nombre": participacion.adoptante.nombre}, user_id=user_id,
                )
        for adoptante in adoptantes:
            if adoptante.id in actuales:
                continue
            participacion = AdoptanteTransferencia(transferencia=transferencia, adoptante=adoptante, created_by=user_id)
            db.session.add(participacion)
            hubo_cambios = True
            AuditoriaService.registrar_evento_relacion(
                entidad="transferencia_socio_productiva", registro_id=transferencia.id,
                relacion="adoptantes", accion="vincular",
                detalle={"adoptante_id": adoptante.id, "nombre": adoptante.nombre}, user_id=user_id,
            )
        return hubo_cambios

    # =================================================
    # VALIDADORES
    # =================================================

    @staticmethod
    def _validar_texto(valor, campo, min_len=3):
        labels = {"denominacion": "la denominación", "demandante": "el demandante", "descripcion_actividad": "la descripción de la actividad"}
        label = labels.get(campo, "este dato")
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label}."}})
        if campo in {"denominacion", "demandante"} and not has_letter(valor):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"{label.capitalize()} debe contener letras."}})

        valor = valor.strip()
        if len(valor) < min_len:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Use al menos {min_len} caracteres para {label}."}})

        return valor


    @staticmethod
    def _validar_monto(monto):
        try:
            monto = float(monto)
        except (TypeError, builtins.ValueError):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"monto": "Ingrese un monto numérico válido."}})

        if not math.isfinite(monto) or monto <= 0:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"monto": "Ingrese un monto mayor que cero."}})

        return monto

    @staticmethod
    def _validar_fecha(valor, campo):
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, builtins.ValueError):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha válida."}})
        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha desde el 01/01/2010."}})
        return fecha


    # =================================================
    # GET ALL
    # =================================================

    @staticmethod
    def _list_query(filters: dict = None):
        query = db.session.query(TransferenciaSocioProductiva).options(
            selectinload(TransferenciaSocioProductiva.participaciones)
            .joinedload(AdoptanteTransferencia.adoptante),
            joinedload(TransferenciaSocioProductiva.tipo_contrato_transferencia),
            joinedload(TransferenciaSocioProductiva.grupo_utn).lazyload("*"),
        )
        filters = filters or {}

        activos = filters.get("activos", "true")

        if activos == "true":
            query = query.filter(
                TransferenciaSocioProductiva.deleted_at.is_(None)
            )
        elif activos == "false":
            query = query.filter(
                TransferenciaSocioProductiva.deleted_at.isnot(None)
            )
        elif activos == "all":
            pass

        if filters.get("grupo_utn_id"):
            query = query.filter(
                TransferenciaSocioProductiva.grupo_utn_id == filters["grupo_utn_id"]
            )

        if filters.get("tipo_contrato_id"):
            query = query.filter(
                TransferenciaSocioProductiva.tipo_contrato_id == filters["tipo_contrato_id"]
            )

        return query.order_by(TransferenciaSocioProductiva.id.asc())

    @staticmethod
    def get_all(filters: dict = None):
        return [t.serialize() for t in TransferenciaSocioProductivaService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int, orden: str = "asc"):
        query = TransferenciaSocioProductivaService._list_query(filters)
        if orden == "desc":
            query = query.order_by(None).order_by(TransferenciaSocioProductiva.id.desc())
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [row.serialize() for row in rows], total

    @staticmethod
    def get_table_page(filters, args):
        query = TransferenciaSocioProductivaService._list_query(filters).outerjoin(
            TransferenciaSocioProductiva.tipo_contrato_transferencia,
        ).outerjoin(TransferenciaSocioProductiva.grupo_utn)
        fields = {"denominacion": TransferenciaSocioProductiva.denominacion,
                  "numero": TransferenciaSocioProductiva.numero_transferencia,
                  "demandante": TransferenciaSocioProductiva.demandante,
                  "descripcion": TransferenciaSocioProductiva.descripcion_actividad,
                  "tipo": TipoContrato.nombre, "grupo": GrupoInvestigacionUtn.nombre_sigla_grupo,
                  "anio": cast(func.extract("year", TransferenciaSocioProductiva.fecha_inicio), Integer)}
        return table_query_page(query, TransferenciaSocioProductiva, args, fields,
                                default_sort="denominacion",
                                searchable=("numero", "denominacion", "demandante", "descripcion", "tipo", "grupo"),
                                facets=("tipo", "grupo", "anio"),
                                extra_search=lambda term: TransferenciaSocioProductiva.participaciones.any(
                                    (AdoptanteTransferencia.deleted_at.is_(None)) &
                                    table_scope_predicate(AdoptanteTransferencia) &
                                    AdoptanteTransferencia.adoptante.has(
                                        table_scope_predicate(Adoptante) &
                                        func.lower(Adoptante.nombre).contains(term, autoescape=True))))


    # =================================================
    # GET BY ID
    # =================================================

    @staticmethod
    def get_by_id(transferencia_id):

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia socio-productiva no encontrada")

        return transferencia.serialize()

    @staticmethod
    def get_historial(transferencia_id):
        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia socio-productiva no encontrada")

        return AuditoriaService.obtener_historial_entidad(
            entidad="transferencia_socio_productiva",
            registro_id=transferencia.id
        )


    # =================================================
    # CREATE
    # =================================================

    @staticmethod
    def create(data: dict, user_id: int):
        if not isinstance(data, dict) or not data:
            raise ValueError("Envíe los datos de la transferencia e intente nuevamente.")

        seleccion_adoptantes = TransferenciaSocioProductivaService._resolver_adoptantes(data)

        denominacion = TransferenciaSocioProductivaService._validar_texto(
            data.get("denominacion"), "denominacion"
        )

        demandante = TransferenciaSocioProductivaService._validar_texto(
            data.get("demandante"), "demandante"
        )

        descripcion_actividad = TransferenciaSocioProductivaService._validar_texto(
            data.get("descripcion_actividad"),
            "descripcion_actividad",
            min_len=10
        )

        monto = TransferenciaSocioProductivaService._validar_monto(
            data.get("monto")
        )

        fecha_inicio = TransferenciaSocioProductivaService._validar_fecha(data.get("fecha_inicio"), "fecha_inicio")

        fecha_fin = None
        if data.get("fecha_fin"):
            fecha_fin = TransferenciaSocioProductivaService._validar_fecha(data["fecha_fin"], "fecha_fin")

            if fecha_fin < fecha_inicio:
                raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_fin": "Ingrese una fecha de fin igual o posterior al inicio."}})

        # Validar relaciones
        tipo_contrato_id = data.get("tipo_contrato_id")
        if isinstance(tipo_contrato_id, bool) or not isinstance(tipo_contrato_id, int) or tipo_contrato_id <= 0:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"tipo_contrato_id": "Seleccione un tipo de contrato disponible."}})
        tipo_contrato = db.session.get(TipoContrato, tipo_contrato_id) if tipo_contrato_id else None
        if not tipo_contrato or tipo_contrato.deleted_at is not None:
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"tipo_contrato_id": "Seleccione un tipo de contrato disponible."}})

        grupo_utn_id = data.get("grupo_utn_id")
        if not grupo_utn_id or not db.session.get(GrupoInvestigacionUtn, grupo_utn_id):
            raise ValueError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

        # Serializa la asignación en PostgreSQL y conserva los números históricos.
        if db.session.get_bind().dialect.name == "postgresql":
            db.session.execute(text("SELECT pg_advisory_xact_lock(71930451)"))
        siguiente_numero = (db.session.query(func.max(TransferenciaSocioProductiva.numero_transferencia)).scalar() or 0) + 1

        transferencia = TransferenciaSocioProductiva(
            numero_transferencia=siguiente_numero,
            denominacion=denominacion,
            demandante=demandante,
            descripcion_actividad=descripcion_actividad,
            monto=monto,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_contrato_id=tipo_contrato_id,
            grupo_utn_id=grupo_utn_id,
            created_by=user_id
        )

        db.session.add(transferencia)
        db.session.flush()
        TransferenciaSocioProductivaService._sincronizar_adoptantes(transferencia, seleccion_adoptantes, user_id)
        db.session.commit()

        return transferencia.serialize()


    # =================================================
    # UPDATE
    # =================================================

    @staticmethod
    def update(transferencia_id, data: dict, user_id: int):

        seleccion_adoptantes = TransferenciaSocioProductivaService._resolver_adoptantes(data)

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia socio-productiva no encontrada")

        if transferencia.deleted_at is not None:
            raise ConflictError("No se puede modificar una transferencia eliminada")

        cambios = {}

        if "denominacion" in data:
            nuevo_valor = TransferenciaSocioProductivaService._validar_texto(
                data["denominacion"], "denominacion"
            )
            cambio = AuditoriaService.construir_cambio(
                transferencia.denominacion,
                nuevo_valor
            )
            if cambio:
                cambios["denominacion"] = cambio
                transferencia.denominacion = nuevo_valor

        if "demandante" in data:
            nuevo_valor = TransferenciaSocioProductivaService._validar_texto(
                data["demandante"], "demandante"
            )
            cambio = AuditoriaService.construir_cambio(
                transferencia.demandante,
                nuevo_valor
            )
            if cambio:
                cambios["demandante"] = cambio
                transferencia.demandante = nuevo_valor

        if "descripcion_actividad" in data:
            nuevo_valor = TransferenciaSocioProductivaService._validar_texto(
                data["descripcion_actividad"],
                "descripcion_actividad",
                min_len=10
            )
            cambio = AuditoriaService.construir_cambio(
                transferencia.descripcion_actividad,
                nuevo_valor
            )
            if cambio:
                cambios["descripcion_actividad"] = cambio
                transferencia.descripcion_actividad = nuevo_valor

        if "monto" in data:
            nuevo_valor = TransferenciaSocioProductivaService._validar_monto(
                data["monto"]
            )
            cambio = AuditoriaService.construir_cambio(
                transferencia.monto,
                nuevo_valor
            )
            if cambio:
                cambios["monto"] = cambio
                transferencia.monto = nuevo_valor

        if "tipo_contrato_id" in data:
            tipo_id = data["tipo_contrato_id"]
            if isinstance(tipo_id, bool) or not isinstance(tipo_id, int) or tipo_id <= 0:
                raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"tipo_contrato_id": "Seleccione un tipo de contrato disponible."}})
            tipo = db.session.get(TipoContrato, tipo_id)
            if not tipo or tipo.deleted_at is not None:
                raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"tipo_contrato_id": "Seleccione un tipo de contrato disponible."}})
            cambio = AuditoriaService.construir_cambio(transferencia.tipo_contrato_id, tipo.id)
            if cambio:
                cambios["tipo_contrato_id"] = cambio
                transferencia.tipo_contrato_id = tipo.id

        if "fecha_inicio" in data:
            nuevo_valor = TransferenciaSocioProductivaService._validar_fecha(data["fecha_inicio"], "fecha_inicio")
            cambio = AuditoriaService.construir_cambio(
                transferencia.fecha_inicio,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_inicio"] = cambio
                transferencia.fecha_inicio = nuevo_valor

        if "fecha_fin" in data:
            nuevo_valor = (
                TransferenciaSocioProductivaService._validar_fecha(data["fecha_fin"], "fecha_fin")
                if data["fecha_fin"] else None
            )
            cambio = AuditoriaService.construir_cambio(
                transferencia.fecha_fin,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_fin"] = cambio
                transferencia.fecha_fin = nuevo_valor

        if (
            transferencia.fecha_fin
            and transferencia.fecha_fin < transferencia.fecha_inicio
        ):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_fin": "Ingrese una fecha de fin igual o posterior al inicio."}})

        hubo_relaciones = TransferenciaSocioProductivaService._sincronizar_adoptantes(transferencia, seleccion_adoptantes, user_id)
        if cambios or hubo_relaciones:
            transferencia.mark_updated(user_id)
        if cambios:
            AuditoriaService.registrar_cambios(
                entidad="transferencia_socio_productiva",
                registro_id=transferencia.id,
                cambios=cambios,
                user_id=user_id
            )

        db.session.commit()
        return transferencia.serialize()


    # =================================================
    # SOFT DELETE
    # =================================================

    @staticmethod
    def delete(transferencia_id, user_id: int):

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia socio-productiva no encontrada")

        if transferencia.deleted_at is not None:
            raise ConflictError("La transferencia ya está eliminada")

        transferencia.soft_delete(user_id)

        db.session.commit()

        return {"message": "Transferencia eliminada correctamente (soft delete)"}


    # =================================================
    # RESTORE
    # =================================================

    @staticmethod
    def restore(transferencia_id):

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia no encontrada")

        transferencia.restore()
        transferencia.activo = True

        db.session.commit()

        return transferencia.serialize()


    # =================================================
    # VINCULAR ADOPTANTES (M:N con entidad intermedia)
    # =================================================

    @staticmethod
    def add_adoptantes(transferencia_id: int, adoptantes_ids: list[int], user_id: int):

        if not isinstance(adoptantes_ids, list) or not adoptantes_ids:
            raise ValueError("Seleccione al menos un adoptante.", details={"fields": {"adoptantes_ids": "Seleccione al menos un adoptante"}})

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )

        if not transferencia:
            raise NotFoundError("Transferencia no encontrada")

        adoptantes = (
            db.session.query(Adoptante)
            .filter(
                Adoptante.id.in_(adoptantes_ids),
                Adoptante.deleted_at.is_(None)
            )
            .all()
        )

        if len(adoptantes) != len(adoptantes_ids):
            raise NotFoundError("Uno o más adoptantes ya no están disponibles", details={"fields": {"adoptantes_ids": "Quite los adoptantes no disponibles y vuelva a intentar"}})

        hubo_cambios = False
        for adoptante in adoptantes:

            existente = db.session.query(AdoptanteTransferencia).filter(
                AdoptanteTransferencia.transferencia_id == transferencia_id,
                AdoptanteTransferencia.adoptante_id == adoptante.id,
                AdoptanteTransferencia.deleted_at.is_(None)
            ).first()

            if existente:
                continue

            nueva = AdoptanteTransferencia(
                transferencia_id=transferencia_id,
                adoptante_id=adoptante.id,
                created_by=user_id
            )

            db.session.add(nueva)
            hubo_cambios = True
            AuditoriaService.registrar_evento_relacion(
                entidad="transferencia_socio_productiva",
                registro_id=transferencia.id,
                relacion="adoptantes",
                accion="vincular",
                detalle={
                    "adoptante_id": adoptante.id,
                    "nombre": adoptante.nombre
                },
                user_id=user_id
            )

        if hubo_cambios:
            transferencia.mark_updated(user_id)

        db.session.commit()

        return transferencia.serialize()


    # =================================================
    # DESVINCULAR ADOPTANTES (SOFT DELETE)
    # =================================================

    @staticmethod
    def remove_adoptantes(transferencia_id: int, adoptantes_ids: list[int], user_id: int):

        if not isinstance(adoptantes_ids, list) or not adoptantes_ids:
            raise ValueError("Seleccione al menos un adoptante.", details={"fields": {"adoptantes_ids": "Seleccione al menos un adoptante"}})

        transferencia = db.session.get(
            TransferenciaSocioProductiva,
            transferencia_id
        )
        hubo_cambios = False

        for adoptante_id in adoptantes_ids:

            participacion = db.session.query(AdoptanteTransferencia).filter(
                AdoptanteTransferencia.transferencia_id == transferencia_id,
                AdoptanteTransferencia.adoptante_id == adoptante_id,
                AdoptanteTransferencia.deleted_at.is_(None)
            ).first()

            if participacion:
                nombre_adoptante = (
                    participacion.adoptante.nombre
                    if getattr(participacion, "adoptante", None) else None
                )
                participacion.soft_delete(user_id)
                hubo_cambios = True
                AuditoriaService.registrar_evento_relacion(
                    entidad="transferencia_socio_productiva",
                    registro_id=transferencia_id,
                    relacion="adoptantes",
                    accion="desvincular",
                    detalle={
                        "adoptante_id": adoptante_id,
                        "nombre": nombre_adoptante
                    },
                    user_id=user_id
                )

        if transferencia and hubo_cambios:
            transferencia.mark_updated(user_id)

        db.session.commit()

        return transferencia.serialize()

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        transferencias = consultar_entidades_memoria(TransferenciaSocioProductiva, memoria_version)

        snapshots = []
        for transferencia in transferencias:
            if not estuvo_activo_en_periodo_memoria(
                memoria_version,
                transferencia.fecha_inicio,
                fin_vigencia(transferencia)
            ):
                continue
            snapshot = TransferenciaSocioProductivaMemoriaVersion(
                memoria_version_id=memoria_version.id,
                transferencia_id=transferencia.id,
                numero_transferencia=transferencia.numero_transferencia,
                denominacion=transferencia.denominacion,
                demandante=transferencia.demandante,
                descripcion_actividad=transferencia.descripcion_actividad,
                monto=transferencia.monto,
                fecha_inicio=transferencia.fecha_inicio,
                fecha_fin=transferencia.fecha_fin,
                tipo_contrato_id=transferencia.tipo_contrato_id,
                tipo_contrato_nombre=(
                    transferencia.tipo_contrato_transferencia.nombre
                    if transferencia.tipo_contrato_transferencia else None
                ),
                grupo_utn_id=transferencia.grupo_utn_id,
                grupo_utn_nombre=(
                    transferencia.grupo_utn.nombre_sigla_grupo
                    if transferencia.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)

            for participacion in transferencia.participaciones:
                if not relacion_vigente_en_memoria(memoria_version, participacion) or participacion.adoptante is None:
                    continue
                if not relacion_vigente_en_memoria(memoria_version, participacion.adoptante):
                    continue

                participacion_snapshot = AdoptanteTransferenciaMemoriaVersion(
                    transferencia_memoria_version=snapshot,
                    adoptante_transferencia_id=participacion.id,
                    adoptante_id=participacion.adoptante.id,
                    adoptante_nombre=participacion.adoptante.nombre,
                    created_by=user_id
                )
                db.session.add(participacion_snapshot)

            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            TransferenciaSocioProductivaMemoriaVersion.query
            .filter(
                TransferenciaSocioProductivaMemoriaVersion.memoria_version_id == memoria_version_id,
                TransferenciaSocioProductivaMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                TransferenciaSocioProductivaMemoriaVersion.fecha_inicio.desc(),
                TransferenciaSocioProductivaMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
