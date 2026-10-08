from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from modules.produccion.services.trabajo_enlace import validar_enlace
from datetime import date, datetime

from sqlalchemy import or_

from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.produccion.models.trabajo_autor import TrabajoRevistaAutor
from modules.produccion.services.trabajo_autores_service import (
    validar_autores, validar_referencias, sincronizar_autores, filtrar_por_autor,
)
from modules.produccion.models.trabajo_revista import (
    TipoRevista,
    TrabajosRevistasReferato,
    TrabajosRevistasReferatoMemoriaVersion,
)
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from extension import db
from modules.shared.services.text_validation import has_letter


class TrabajosRevistasReferatoService:

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str, permitir_none: bool = False):
        if valor is None and permitir_none:
            return None

        if not isinstance(valor, int) or valor <= 0:
            if campo == "tipo_revista_id":
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Seleccione un tipo de revista disponible."}})
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")

        return valor

    @staticmethod
    def _validar_user_id(user_id: int):
        return TrabajosRevistasReferatoService._validar_id(user_id, "user_id")

    @staticmethod
    def _validar_texto(valor: str, campo: str, max_len: int = 255):
        labels = {"titulo_trabajo": "el título del trabajo", "nombre_revista": "el nombre de la revista", "editorial": "la editorial", "issn": "el ISSN", "pais": "el país"}
        label = labels.get(campo, "este dato")
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label}."}})
        if campo == "nombre_revista" and not has_letter(valor):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "El nombre de la revista debe contener letras."}})

        valor = " ".join(valor.strip().split())

        if len(valor) > max_len:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Use hasta {max_len} caracteres para {label}."}})

        return valor

    @staticmethod
    def _validar_fecha_publicacion(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha de publicación válida."}})

        if fecha > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha de publicación que no sea futura."}})

        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_publicacion": "Ingrese una fecha de publicación desde el 01/01/2010."}})
        return fecha

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _normalizar_orden(orden):
        if orden is None:
            return None
        return str(orden).strip().lower()

    @staticmethod
    def _normalizar_texto_filtro(valor):
        if valor is None:
            return None
        valor = " ".join(str(valor).strip().split())
        return valor or None

    @staticmethod
    def _parse_int_filter(valor, campo: str):
        if valor is None or valor == "":
            return None

        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise ValidationError(f"El campo '{campo}' debe ser un entero positivo")

        return TrabajosRevistasReferatoService._validar_id(valor, campo)

    @staticmethod
    def _validar_grupo(grupo_utn_id):
        grupo_utn_id = TrabajosRevistasReferatoService._validar_id(
            grupo_utn_id, "grupo_utn_id", permitir_none=True
        )

        if grupo_utn_id is None:
            return None

        grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id)
        if not grupo or getattr(grupo, "deleted_at", None) is not None:
            raise NotFoundError("Grupo UTN invalido")

        return grupo.id

    @staticmethod
    def _validar_tipo_revista(tipo_revista_id):
        tipo_revista_id = TrabajosRevistasReferatoService._validar_id(
            tipo_revista_id, "tipo_revista_id"
        )
        tipo_revista = db.session.get(TipoRevista, tipo_revista_id)
        if not tipo_revista or tipo_revista.deleted_at is not None:
            raise NotFoundError("El tipo de revista ya no está disponible. Elija otro e intente nuevamente.", details={"fields": {"tipo_revista_id": "Seleccione un tipo de revista disponible."}})
        return tipo_revista.id

    @staticmethod
    def _get_or_404(trabajo_id: int):
        trabajo = db.session.get(
            TrabajosRevistasReferato,
            TrabajosRevistasReferatoService._validar_id(
                trabajo_id, "trabajo_id"
            )
        )

        if not trabajo:
            raise NotFoundError("Trabajo en revista no encontrado")

        return trabajo

    @staticmethod
    def _get_activo_or_404(trabajo_id: int):
        trabajo = TrabajosRevistasReferatoService._get_or_404(trabajo_id)

        if trabajo.deleted_at is not None:
            raise ConflictError("No se puede operar sobre un trabajo eliminado")

        return trabajo

    @staticmethod
    def _validar_no_duplicado(
        titulo_trabajo: str,
        nombre_revista: str,
        editorial: str,
        issn: str,
        pais: str,
        fecha_publicacion,
        trabajo_id: int = None
    ):
        query = TrabajosRevistasReferato.query.filter(
            TrabajosRevistasReferato.deleted_at.is_(None),
            TrabajosRevistasReferato.titulo_trabajo == titulo_trabajo,
            TrabajosRevistasReferato.nombre_revista == nombre_revista,
            TrabajosRevistasReferato.editorial == editorial,
            TrabajosRevistasReferato.issn == issn,
            TrabajosRevistasReferato.pais == pais,
            TrabajosRevistasReferato.fecha_publicacion == fecha_publicacion,
        )

        if trabajo_id is not None:
            query = query.filter(TrabajosRevistasReferato.id != trabajo_id)

        if query.first():
            raise ConflictError("Ya existe un trabajo de revista con los mismos datos. Revise el título, la revista y la fecha antes de reintentar.")

    @staticmethod
    def _list_query(filters: dict = None):
        filters = filters or {}
        query = filtrar_por_autor(TrabajosRevistasReferato.query, TrabajosRevistasReferato, TrabajoRevistaAutor, filters)

        activos = TrabajosRevistasReferatoService._normalizar_activos(
            filters.get("activos")
        )
        if activos == "true":
            query = query.filter(
                TrabajosRevistasReferato.deleted_at.is_(None),
                TrabajosRevistasReferato.activo.is_(True)
            )
        elif activos == "false":
            query = query.filter(
                or_(
                    TrabajosRevistasReferato.deleted_at.isnot(None),
                    TrabajosRevistasReferato.activo.is_(False)
                )
            )
        elif activos != "all":
            query = query.filter(
                TrabajosRevistasReferato.deleted_at.is_(None),
                TrabajosRevistasReferato.activo.is_(True)
            )

        grupo_utn_id = TrabajosRevistasReferatoService._parse_int_filter(
            filters.get("grupo_utn_id"), "grupo_utn_id"
        )
        if grupo_utn_id is not None:
            query = query.filter(
                TrabajosRevistasReferato.grupo_utn_id == grupo_utn_id
            )

        pais = TrabajosRevistasReferatoService._normalizar_texto_filtro(
            filters.get("pais")
        )
        if pais:
            query = query.filter(TrabajosRevistasReferato.pais.ilike(f"%{pais}%"))

        editorial = TrabajosRevistasReferatoService._normalizar_texto_filtro(
            filters.get("editorial")
        )
        if editorial:
            query = query.filter(
                TrabajosRevistasReferato.editorial.ilike(f"%{editorial}%")
            )

        orden = TrabajosRevistasReferatoService._normalizar_orden(
            filters.get("orden")
        )
        if orden == "asc":
            query = query.order_by(TrabajosRevistasReferato.fecha_publicacion.asc())
        else:
            query = query.order_by(TrabajosRevistasReferato.fecha_publicacion.desc())

        return query.order_by(TrabajosRevistasReferato.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [t.serialize() for t in TrabajosRevistasReferatoService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = TrabajosRevistasReferatoService._list_query(filters)
        total = query.count()
        return [t.serialize() for t in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_by_id(trabajo_id: int):
        return TrabajosRevistasReferatoService._get_or_404(trabajo_id).serialize()

    @staticmethod
    def get_historial(trabajo_id: int):
        trabajo = TrabajosRevistasReferatoService._get_or_404(trabajo_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="trabajo_revista_referato",
            registro_id=trabajo.id
        )

    @staticmethod
    def create(data: dict, user_id: int):
        TrabajosRevistasReferatoService._validar_payload(data)
        TrabajosRevistasReferatoService._validar_user_id(user_id)

        titulo_trabajo = TrabajosRevistasReferatoService._validar_texto(
            data.get("titulo_trabajo"), "titulo_trabajo"
        )
        nombre_revista = TrabajosRevistasReferatoService._validar_texto(
            data.get("nombre_revista"), "nombre_revista"
        )
        editorial = TrabajosRevistasReferatoService._validar_texto(
            data.get("editorial"), "editorial"
        )
        issn = TrabajosRevistasReferatoService._validar_texto(
            data.get("issn"), "issn", max_len=50
        )
        pais = TrabajosRevistasReferatoService._validar_texto(
            data.get("pais"), "pais", max_len=120
        )
        fecha_publicacion = TrabajosRevistasReferatoService._validar_fecha_publicacion(
            data.get("fecha_publicacion")
        )
        grupo_utn_id = TrabajosRevistasReferatoService._validar_grupo(
            data.get("grupo_utn_id")
        )
        tipo_revista_id = TrabajosRevistasReferatoService._validar_tipo_revista(
            data.get("tipo_revista_id")
        )

        TrabajosRevistasReferatoService._validar_no_duplicado(
            titulo_trabajo,
            nombre_revista,
            editorial,
            issn,
            pais,
            fecha_publicacion,
        )

        enlace = validar_enlace(data.get("enlace"))
        autores = validar_autores(data.get("autores", []))

        trabajo = TrabajosRevistasReferato(
            titulo_trabajo=titulo_trabajo,
            nombre_revista=nombre_revista,
            editorial=editorial,
            issn=issn,
            fecha_publicacion=fecha_publicacion,
            pais=pais,
            grupo_utn_id=grupo_utn_id,
            tipo_revista_id=tipo_revista_id,
            enlace=enlace,
            created_by=user_id
        )

        try:
            db.session.add(trabajo)
            db.session.flush()
            sincronizar_autores(trabajo, autores, TrabajoRevistaAutor, "trabajo_revista_referato", user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def update(trabajo_id: int, data: dict, user_id: int):
        TrabajosRevistasReferatoService._validar_payload(data)
        TrabajosRevistasReferatoService._validar_user_id(user_id)
        trabajo = TrabajosRevistasReferatoService._get_activo_or_404(trabajo_id)
        autores = validar_autores(data["autores"], trabajo.autorias) if "autores" in data else None
        enlace = validar_enlace(data["enlace"]) if "enlace" in data else trabajo.enlace
        cambios = {}

        titulo_trabajo = trabajo.titulo_trabajo
        if "titulo_trabajo" in data:
            titulo_trabajo = TrabajosRevistasReferatoService._validar_texto(
                data["titulo_trabajo"], "titulo_trabajo"
            )

        nombre_revista = trabajo.nombre_revista
        if "nombre_revista" in data:
            nombre_revista = TrabajosRevistasReferatoService._validar_texto(
                data["nombre_revista"], "nombre_revista"
            )

        editorial = trabajo.editorial
        if "editorial" in data:
            editorial = TrabajosRevistasReferatoService._validar_texto(
                data["editorial"], "editorial"
            )

        issn = trabajo.issn
        if "issn" in data:
            issn = TrabajosRevistasReferatoService._validar_texto(
                data["issn"], "issn", max_len=50
            )

        pais = trabajo.pais
        if "pais" in data:
            pais = TrabajosRevistasReferatoService._validar_texto(
                data["pais"], "pais", max_len=120
            )

        fecha_publicacion = trabajo.fecha_publicacion
        if "fecha_publicacion" in data:
            fecha_publicacion = TrabajosRevistasReferatoService._validar_fecha_publicacion(
                data["fecha_publicacion"]
            )

        grupo_utn_id = trabajo.grupo_utn_id
        if "grupo_utn_id" in data:
            grupo_utn_id = TrabajosRevistasReferatoService._validar_grupo(
                data["grupo_utn_id"]
            )

        tipo_revista_id = trabajo.tipo_revista_id
        if "tipo_revista_id" in data:
            tipo_revista_id = TrabajosRevistasReferatoService._validar_tipo_revista(
                data["tipo_revista_id"]
            )

        TrabajosRevistasReferatoService._validar_no_duplicado(
            titulo_trabajo,
            nombre_revista,
            editorial,
            issn,
            pais,
            fecha_publicacion,
            trabajo.id,
        )

        try:
            cambio = AuditoriaService.construir_cambio(
                trabajo.titulo_trabajo,
                titulo_trabajo
            )
            if cambio:
                cambios["titulo_trabajo"] = cambio
                trabajo.titulo_trabajo = titulo_trabajo

            cambio = AuditoriaService.construir_cambio(
                trabajo.nombre_revista,
                nombre_revista
            )
            if cambio:
                cambios["nombre_revista"] = cambio
                trabajo.nombre_revista = nombre_revista

            cambio = AuditoriaService.construir_cambio(
                trabajo.editorial,
                editorial
            )
            if cambio:
                cambios["editorial"] = cambio
                trabajo.editorial = editorial

            cambio = AuditoriaService.construir_cambio(trabajo.issn, issn)
            if cambio:
                cambios["issn"] = cambio
                trabajo.issn = issn

            cambio = AuditoriaService.construir_cambio(trabajo.pais, pais)
            if cambio:
                cambios["pais"] = cambio
                trabajo.pais = pais

            cambio = AuditoriaService.construir_cambio(
                trabajo.fecha_publicacion,
                fecha_publicacion,
            )
            if cambio:
                cambios["fecha_publicacion"] = cambio
                trabajo.fecha_publicacion = fecha_publicacion

            cambio = AuditoriaService.construir_cambio(
                trabajo.grupo_utn_id,
                grupo_utn_id
            )
            if cambio:
                cambios["grupo_utn_id"] = cambio
                trabajo.grupo_utn_id = grupo_utn_id

            cambio = AuditoriaService.construir_cambio(
                trabajo.tipo_revista_id,
                tipo_revista_id
            )
            if cambio:
                cambios["tipo_revista_id"] = cambio
                trabajo.tipo_revista_id = tipo_revista_id

            cambio = AuditoriaService.construir_cambio(trabajo.enlace, enlace)
            if cambio:
                cambios["enlace"] = cambio
                trabajo.enlace = enlace

            if cambios:
                trabajo.mark_updated(user_id)
                AuditoriaService.registrar_cambios(
                    entidad="trabajo_revista_referato",
                    registro_id=trabajo.id,
                    cambios=cambios,
                    user_id=user_id
                )

            if autores is not None:
                sincronizar_autores(trabajo, autores, TrabajoRevistaAutor, "trabajo_revista_referato", user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def delete(trabajo_id: int, user_id: int):
        TrabajosRevistasReferatoService._validar_user_id(user_id)
        trabajo = TrabajosRevistasReferatoService._get_activo_or_404(trabajo_id)
        trabajo.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Trabajo eliminado correctamente (soft delete)"}

    @staticmethod
    def restore(trabajo_id: int):
        trabajo = TrabajosRevistasReferatoService._get_or_404(trabajo_id)

        if trabajo.deleted_at is None and trabajo.activo is True:
            raise ConflictError("El trabajo ya se encuentra activo")

        trabajo.restore()
        trabajo.activo = True

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def desvincular_autores(trabajo_id, autores, user_id):
        TrabajosRevistasReferatoService._validar_user_id(user_id)
        trabajo = TrabajosRevistasReferatoService._get_activo_or_404(trabajo_id)
        claves = set(validar_referencias(autores))
        restantes = [{"rol": a.rol, "id": a.integrante.id} for a in trabajo.autorias
                     if (a.rol, a.integrante.id) not in claves]
        return TrabajosRevistasReferatoService.update(trabajo_id, {"autores": restantes}, user_id)

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        trabajos = consultar_entidades_memoria(TrabajosRevistasReferato, memoria_version)

        snapshots = []
        for trabajo in trabajos:
            if not registro_puntual_en_memoria(
                memoria_version,
                trabajo,
                trabajo.fecha_publicacion,
            ):
                continue
            autores = [autor.serialize() for autor in trabajo.autorias]

            snapshot = TrabajosRevistasReferatoMemoriaVersion(
                memoria_version_id=memoria_version.id,
                trabajo_revista_id=trabajo.id,
                enlace=trabajo.enlace,
                titulo_trabajo=trabajo.titulo_trabajo,
                nombre_revista=trabajo.nombre_revista,
                editorial=trabajo.editorial,
                issn=trabajo.issn,
                pais=trabajo.pais,
                fecha_publicacion=trabajo.fecha_publicacion,
                grupo_utn_id=trabajo.grupo_utn_id,
                grupo_utn_nombre=(
                    trabajo.grupo_utn.nombre_sigla_grupo
                    if trabajo.grupo_utn else None
                ),
                tipo_revista_id=trabajo.tipo_revista_id,
                tipo_revista_nombre=(
                    trabajo.tipo_revista.nombre
                    if trabajo.tipo_revista else None
                ),
                autores=autores,
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            TrabajosRevistasReferatoMemoriaVersion.query
            .filter(
                TrabajosRevistasReferatoMemoriaVersion.memoria_version_id == memoria_version_id,
                TrabajosRevistasReferatoMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                TrabajosRevistasReferatoMemoriaVersion.fecha_publicacion.desc(),
                TrabajosRevistasReferatoMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
