from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from datetime import datetime, date

from extension import db
from modules.shared.exceptions import NotFoundError, ValidationError
from modules.produccion.models.articulo_divulgacion import (
    ArticuloDivulgacion,
    ArticuloDivulgacionMemoriaVersion,
)
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria


class ArticuloDivulgacionService:
    @staticmethod
    def _validar_payload(data):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos enviados son invalidos")

    @staticmethod
    def _validar_user_id(user_id):
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")
        return user_id

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _validar_texto(valor, campo, min_len=3, max_len=500):
        label = "el título" if campo == "titulo" else "la descripción"
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label} del artículo."}})

        valor = valor.strip()
        if not min_len <= len(valor) <= max_len:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Use entre {min_len} y {max_len} caracteres para {label}."}})

        return valor

    @staticmethod
    def _validar_fecha(fecha_publicacion):
        if fecha_publicacion < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha desde el 01/01/2010."}})
        if fecha_publicacion > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha que no sea futura."}})

    @staticmethod
    def _validar_grupo(grupo_utn_id):
        if not isinstance(grupo_utn_id, int) or grupo_utn_id <= 0:
            raise ValidationError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

        grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id)
        if not grupo or grupo.deleted_at is not None:
            raise ValidationError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")

        return grupo_utn_id

    @staticmethod
    def _get_articulo_activo_or_404(articulo_id: int):
        articulo = ArticuloDivulgacion.query.filter(
            ArticuloDivulgacion.id == articulo_id,
            ArticuloDivulgacion.deleted_at.is_(None)
        ).first()

        if not articulo:
            raise NotFoundError("Articulo de divulgacion no encontrado")

        return articulo

    @staticmethod
    def _list_query(filters: dict = None):
        query = ArticuloDivulgacion.query
        filters = filters or {"activos": "true"}

        activos = ArticuloDivulgacionService._normalizar_activos(
            filters.get("activos")
        )
        if activos == "true":
            query = query.filter(ArticuloDivulgacion.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(ArticuloDivulgacion.deleted_at.isnot(None))
        elif activos != "all":
            query = query.filter(ArticuloDivulgacion.deleted_at.is_(None))

        grupo_id = filters.get("grupo_utn_id")
        if grupo_id:
            query = query.filter(ArticuloDivulgacion.grupo_utn_id == grupo_id)

        orden = filters.get("orden")
        if orden == "asc":
            query = query.order_by(ArticuloDivulgacion.fecha_publicacion.asc())
        else:
            query = query.order_by(ArticuloDivulgacion.fecha_publicacion.desc())

        return query.order_by(ArticuloDivulgacion.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [a.serialize() for a in ArticuloDivulgacionService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = ArticuloDivulgacionService._list_query(filters)
        total = query.count()
        return [a.serialize() for a in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_by_id(articulo_id: int):
        articulo = db.session.get(ArticuloDivulgacion, articulo_id)
        if not articulo:
            raise NotFoundError("Articulo de divulgacion no encontrado")

        return articulo.serialize()

    @staticmethod
    def get_historial(articulo_id: int):
        articulo = db.session.get(ArticuloDivulgacion, articulo_id)
        if not articulo:
            raise NotFoundError("Articulo de divulgacion no encontrado")

        return AuditoriaService.obtener_historial_entidad(
            entidad="articulo_divulgacion",
            registro_id=articulo.id
        )

    @staticmethod
    def create(data: dict, user_id: int):
        ArticuloDivulgacionService._validar_payload(data)
        ArticuloDivulgacionService._validar_user_id(user_id)

        try:
            fecha_publicacion = datetime.strptime(
                data["fecha_publicacion"], "%Y-%m-%d"
            ).date()
        except (KeyError, TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha válida."}})

        ArticuloDivulgacionService._validar_fecha(fecha_publicacion)

        titulo = ArticuloDivulgacionService._validar_texto(
            data.get("titulo"), "titulo", min_len=5
        )
        descripcion = ArticuloDivulgacionService._validar_texto(
            data.get("descripcion"), "descripcion", min_len=10
        )
        grupo_utn_id = ArticuloDivulgacionService._validar_grupo(
            data.get("grupo_utn_id")
        )

        articulo = ArticuloDivulgacion(
            titulo=titulo,
            descripcion=descripcion,
            fecha_publicacion=fecha_publicacion,
            grupo_utn_id=grupo_utn_id,
            created_by=user_id
        )

        db.session.add(articulo)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return articulo.serialize()

    @staticmethod
    def update(articulo_id: int, data: dict, user_id: int = None):
        ArticuloDivulgacionService._validar_payload(data)

        if user_id is not None:
            ArticuloDivulgacionService._validar_user_id(user_id)

        articulo = ArticuloDivulgacionService._get_articulo_activo_or_404(
            articulo_id
        )
        cambios = {}

        if "fecha_publicacion" in data:
            try:
                nuevo_valor = datetime.strptime(
                    data["fecha_publicacion"], "%Y-%m-%d"
                ).date()
            except (TypeError, ValueError):
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha válida."}})

            ArticuloDivulgacionService._validar_fecha(nuevo_valor)
            cambio = AuditoriaService.construir_cambio(
                articulo.fecha_publicacion,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_publicacion"] = cambio
                articulo.fecha_publicacion = nuevo_valor

        if "titulo" in data:
            nuevo_valor = ArticuloDivulgacionService._validar_texto(
                data["titulo"], "titulo", min_len=5
            )
            cambio = AuditoriaService.construir_cambio(
                articulo.titulo,
                nuevo_valor
            )
            if cambio:
                cambios["titulo"] = cambio
                articulo.titulo = nuevo_valor

        if "descripcion" in data:
            nuevo_valor = ArticuloDivulgacionService._validar_texto(
                data["descripcion"], "descripcion", min_len=10
            )
            cambio = AuditoriaService.construir_cambio(
                articulo.descripcion,
                nuevo_valor
            )
            if cambio:
                cambios["descripcion"] = cambio
                articulo.descripcion = nuevo_valor

        if "grupo_utn_id" in data:
            nuevo_valor = ArticuloDivulgacionService._validar_grupo(
                data["grupo_utn_id"]
            )
            cambio = AuditoriaService.construir_cambio(
                articulo.grupo_utn_id,
                nuevo_valor
            )
            if cambio:
                cambios["grupo_utn_id"] = cambio
                articulo.grupo_utn_id = nuevo_valor

        if cambios and user_id is not None:
            articulo.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="articulo_divulgacion",
                registro_id=articulo.id,
                cambios=cambios,
                user_id=user_id
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return articulo.serialize()

    @staticmethod
    def delete(articulo_id: int, user_id: int):
        ArticuloDivulgacionService._validar_user_id(user_id)
        articulo = ArticuloDivulgacionService._get_articulo_activo_or_404(
            articulo_id
        )

        articulo.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Articulo de divulgacion eliminado correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        articulos = consultar_entidades_memoria(ArticuloDivulgacion, memoria_version)

        snapshots = []
        for articulo in articulos:
            if not registro_puntual_en_memoria(memoria_version, articulo, articulo.fecha_publicacion):
                continue
            snapshot = ArticuloDivulgacionMemoriaVersion(
                memoria_version_id=memoria_version.id,
                articulo_divulgacion_id=articulo.id,
                titulo=articulo.titulo,
                descripcion=articulo.descripcion,
                fecha_publicacion=articulo.fecha_publicacion,
                grupo_utn_id=articulo.grupo_utn_id,
                grupo_utn_nombre=(
                    articulo.grupo_utn.nombre_sigla_grupo
                    if articulo.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            ArticuloDivulgacionMemoriaVersion.query
            .filter(
                ArticuloDivulgacionMemoriaVersion.memoria_version_id == memoria_version_id,
                ArticuloDivulgacionMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                ArticuloDivulgacionMemoriaVersion.fecha_publicacion.desc(),
                ArticuloDivulgacionMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
