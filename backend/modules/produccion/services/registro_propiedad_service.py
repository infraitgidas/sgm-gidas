from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from datetime import datetime, date

from sqlalchemy import or_

from extension import db
from modules.shared.services.text_validation import has_letter
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.produccion.models.registro_patente import (
    RegistrosPropiedad,
    TipoRegistroPropiedad,
    RegistrosPropiedadMemoriaVersion,
)
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria


class RegistrosPropiedadService:

    # =========================
    # HELPERS
    # =========================
    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or valor <= 0:
            if campo == "tipo_registro_id":
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Seleccione un tipo de registro disponible."}})
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")
        return valor

    @staticmethod
    def _validar_texto(valor: str, campo: str):
        if not isinstance(valor, str) or not valor.strip():
            labels = {"nombre_articulo": "el nombre del artículo", "organismo_registrante": "el organismo registrante"}
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {labels.get(campo, 'este dato')}."}})
        if campo == "nombre_articulo" and not has_letter(valor):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "El nombre del artículo debe contener letras."}})
        return " ".join(valor.strip().split())

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _validar_fecha(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (KeyError, TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_registro": "Ingrese una fecha válida."}})

        if fecha > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_registro": "Ingrese una fecha que no sea futura."}})

        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_registro": "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

    @staticmethod
    def _get_or_404(registro_id: int):
        registro = db.session.get(
            RegistrosPropiedad,
            RegistrosPropiedadService._validar_id(registro_id, "registro_id")
        )
        if not registro:
            raise NotFoundError("Registro de propiedad no encontrado")
        return registro

    @staticmethod
    def _validar_tipo_registro(tipo_registro_id):
        tipo_registro_id = RegistrosPropiedadService._validar_id(
            tipo_registro_id, "tipo_registro_id"
        )
        tipo_registro = db.session.get(TipoRegistroPropiedad, tipo_registro_id)
        if not tipo_registro:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"tipo_registro_id": "Seleccione un tipo de registro disponible."}})
        return tipo_registro.id

    @staticmethod
    def _validar_grupo(grupo_utn_id):
        grupo_utn_id = RegistrosPropiedadService._validar_id(
            grupo_utn_id, "grupo_utn_id"
        )
        grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id)
        if not grupo or grupo.deleted_at is not None:
            raise ValidationError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")
        return grupo.id

    # =========================
    # LISTAR
    # =========================
    @staticmethod
    def _list_query(activos: str = "true"):
        query = RegistrosPropiedad.query

        activos = RegistrosPropiedadService._normalizar_activos(activos)

        if activos == "true":
            query = query.filter(
                RegistrosPropiedad.deleted_at.is_(None),
                RegistrosPropiedad.activo.is_(True)
            )
        elif activos == "false":
            query = query.filter(
                or_(
                    RegistrosPropiedad.deleted_at.isnot(None),
                    RegistrosPropiedad.activo.is_(False)
                )
            )
        elif activos == "all":
            pass
        else:
            query = query.filter(
                RegistrosPropiedad.deleted_at.is_(None),
                RegistrosPropiedad.activo.is_(True)
            )

        return query.order_by(RegistrosPropiedad.id.asc())

    @staticmethod
    def get_all(activos: str = "true"):
        return [r.serialize() for r in RegistrosPropiedadService._list_query(activos).all()]

    @staticmethod
    def get_page(activos: str, page: int, per_page: int, orden: str = "asc"):
        query = RegistrosPropiedadService._list_query(activos).order_by(None)
        total = query.count()
        direction = RegistrosPropiedad.id.desc() if orden == "desc" else RegistrosPropiedad.id.asc()
        return [r.serialize() for r in query.order_by(direction).offset((page - 1) * per_page).limit(per_page).all()], total

    # =========================
    # OBTENER POR ID
    # =========================
    @staticmethod
    def get_by_id(registro_id: int):
        registro = RegistrosPropiedadService._get_or_404(registro_id)
        return registro.serialize()

    @staticmethod
    def get_historial(registro_id: int):
        registro = RegistrosPropiedadService._get_or_404(registro_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="registro_propiedad",
            registro_id=registro.id
        )

    # =========================
    # CREAR
    # =========================
    @staticmethod
    def create(data: dict, user_id: int):
        RegistrosPropiedadService._validar_payload(data)
        RegistrosPropiedadService._validar_id(user_id, "user_id")

        fecha_registro = RegistrosPropiedadService._validar_fecha(
            data.get("fecha_registro")
        )

        nuevo = RegistrosPropiedad(
            nombre_articulo=RegistrosPropiedadService._validar_texto(
                data.get("nombre_articulo"), "nombre_articulo"
            ),
            organismo_registrante=RegistrosPropiedadService._validar_texto(
                data.get("organismo_registrante"), "organismo_registrante"
            ),
            fecha_registro=fecha_registro,
            tipo_registro_id=RegistrosPropiedadService._validar_tipo_registro(
                data.get("tipo_registro_id")
            ),
            grupo_utn_id=RegistrosPropiedadService._validar_grupo(
                data.get("grupo_utn_id")
            ),
            created_by=user_id,
        )

        db.session.add(nuevo)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return nuevo.serialize()

    # =========================
    # ACTUALIZAR
    # =========================
    @staticmethod
    def update(registro_id: int, data: dict, user_id: int):
        RegistrosPropiedadService._validar_payload(data)
        RegistrosPropiedadService._validar_id(user_id, "user_id")
        registro = RegistrosPropiedadService._get_or_404(registro_id)
        cambios = {}

        if not registro.activo:
            raise ConflictError(
                "No se puede modificar un registro eliminado. Restaurarlo primero."
            )

        if "nombre_articulo" in data:
            nuevo_valor = RegistrosPropiedadService._validar_texto(
                data.get("nombre_articulo"), "nombre_articulo"
            )
            cambio = AuditoriaService.construir_cambio(
                registro.nombre_articulo,
                nuevo_valor
            )
            if cambio:
                cambios["nombre_articulo"] = cambio
                registro.nombre_articulo = nuevo_valor

        if "organismo_registrante" in data:
            nuevo_valor = RegistrosPropiedadService._validar_texto(
                data.get("organismo_registrante"), "organismo_registrante"
            )
            cambio = AuditoriaService.construir_cambio(
                registro.organismo_registrante,
                nuevo_valor
            )
            if cambio:
                cambios["organismo_registrante"] = cambio
                registro.organismo_registrante = nuevo_valor

        if "tipo_registro_id" in data:
            nuevo_valor = RegistrosPropiedadService._validar_tipo_registro(
                data.get("tipo_registro_id")
            )
            cambio = AuditoriaService.construir_cambio(
                registro.tipo_registro_id,
                nuevo_valor
            )
            if cambio:
                cambios["tipo_registro_id"] = cambio
                registro.tipo_registro_id = nuevo_valor

        if "grupo_utn_id" in data:
            nuevo_valor = RegistrosPropiedadService._validar_grupo(
                data.get("grupo_utn_id")
            )
            cambio = AuditoriaService.construir_cambio(
                registro.grupo_utn_id,
                nuevo_valor
            )
            if cambio:
                cambios["grupo_utn_id"] = cambio
                registro.grupo_utn_id = nuevo_valor

        if "fecha_registro" in data:
            nuevo_valor = RegistrosPropiedadService._validar_fecha(data["fecha_registro"])

            cambio = AuditoriaService.construir_cambio(
                registro.fecha_registro,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_registro"] = cambio
                registro.fecha_registro = nuevo_valor

        if cambios:
            registro.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="registro_propiedad",
                registro_id=registro.id,
                cambios=cambios,
                user_id=user_id
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return registro.serialize()

    # =========================
    # SOFT DELETE
    # =========================
    @staticmethod
    def delete(registro_id: int, user_id: int):
        RegistrosPropiedadService._validar_id(user_id, "user_id")
        registro = RegistrosPropiedadService._get_or_404(registro_id)

        if not registro.activo:
            raise ConflictError("El registro ya se encuentra eliminado.")

        registro.soft_delete(user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Registro eliminado correctamente (soft delete)"}

    # =========================
    # RESTORE
    # =========================
    @staticmethod
    def restore(registro_id: int):
        registro = RegistrosPropiedadService._get_or_404(registro_id)

        if registro.activo:
            raise ConflictError("El registro ya se encuentra activo.")

        registro.restore()
        registro.activo = True

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return registro.serialize()

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        registros = consultar_entidades_memoria(RegistrosPropiedad, memoria_version)

        snapshots = []
        for registro in registros:
            if not registro_puntual_en_memoria(memoria_version, registro, registro.fecha_registro):
                continue
            snapshot = RegistrosPropiedadMemoriaVersion(
                memoria_version_id=memoria_version.id,
                registro_propiedad_id=registro.id,
                nombre_articulo=registro.nombre_articulo,
                organismo_registrante=registro.organismo_registrante,
                fecha_registro=registro.fecha_registro,
                tipo_registro_id=registro.tipo_registro_id,
                tipo_registro_nombre=(
                    registro.tipo_registro.nombre
                    if registro.tipo_registro else None
                ),
                grupo_utn_id=registro.grupo_utn_id,
                grupo_utn_nombre=(
                    registro.grupo_utn.nombre_sigla_grupo
                    if registro.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            RegistrosPropiedadMemoriaVersion.query
            .filter(
                RegistrosPropiedadMemoriaVersion.memoria_version_id == memoria_version_id,
                RegistrosPropiedadMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                RegistrosPropiedadMemoriaVersion.fecha_registro.desc(),
                RegistrosPropiedadMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
