from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from datetime import datetime
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload
from modules.shared.controllers.pagination import table_query_page, table_scope_predicate

from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.produccion.models.documentacion_autores import (
    DocumentacionBibliografica,
    Autor,
    DocumentacionBibliograficaMemoriaVersion,
    DocumentacionBibliograficaAutorMemoriaVersion,
)
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE


DOCUMENTACION_HISTORY_FIELDS = frozenset({"titulo", "editorial", "anio", "fecha", "grupo_id"})


class DocumentacionBibliograficaService:

    # =========================
    # Helpers
    # =========================

    @staticmethod
    def _get_activo_or_404(doc_id: int):
        doc = db.session.get(DocumentacionBibliografica, doc_id)
        if not doc or doc.deleted_at is not None:
            raise NotFoundError("Documentacion bibliografica no encontrada")
        return doc

    @staticmethod
    def _normalizar_texto(valor: str, campo: str):
        if not isinstance(valor, str) or not valor.strip():
            key = campo.lower()
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {key: f"Ingrese {('el título' if key == 'titulo' else 'la editorial')} de la documentación."}})

        return " ".join(valor.strip().split()).lower()

    @staticmethod
    def _parse_fecha(valor, campo="fecha"):
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha válida."}})
        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

    # =========================
    # GET ALL
    # =========================
    @staticmethod
    def _list_query(filters: dict = None):
        query = DocumentacionBibliografica.query.options(
            joinedload(DocumentacionBibliografica.grupo_utn).lazyload("*"),
            selectinload(DocumentacionBibliografica.autores),
        )

        if not filters:
            filters = {"activos": "true"}

        activos = filters.get("activos", "true")
        if activos is None:
            activos = "true"

        activos = activos.strip().lower()

        if activos == "true":
            query = query.filter(DocumentacionBibliografica.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(DocumentacionBibliografica.deleted_at.isnot(None))
        elif activos == "all":
            pass
        else:
            query = query.filter(DocumentacionBibliografica.deleted_at.is_(None))

        if filters:
            orden = filters.get("orden")
            if orden == "asc":
                query = query.order_by(DocumentacionBibliografica.titulo.asc())
            elif orden == "desc":
                query = query.order_by(DocumentacionBibliografica.titulo.desc())

        return query.order_by(DocumentacionBibliografica.id.asc())

    @staticmethod
    def get_all(filters: dict = None):
        return [d.serialize() for d in DocumentacionBibliograficaService._list_query(filters).all()]

    @staticmethod
    def get_table_page(filters, args):
        doc = DocumentacionBibliografica
        fields = {"titulo": doc.titulo, "editorial": doc.editorial,
                  "anio": doc.anio, "autor": Autor.nombre_apellido}
        def author_condition(value, search=False):
            name = func.lower(func.trim(Autor.nombre_apellido))
            match = name.contains(value.lower(), autoescape=True) if search else name == value.lower()
            return doc.autores.any(Autor.deleted_at.is_(None) & table_scope_predicate(Autor) & match)
        return table_query_page(
            DocumentacionBibliograficaService._list_query(filters), doc, args, fields,
            default_sort="titulo", sortable=("titulo", "editorial", "anio"),
            searchable=("titulo", "editorial", "anio"),
            facets=("autor", "anio"), extra_search=lambda value: author_condition(value, True),
            facet_joins={"autor": lambda scoped: scoped.join(doc.autores).filter(
                Autor.deleted_at.is_(None), table_scope_predicate(Autor))},
            filter_conditions={"autor": author_condition},
        )

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = DocumentacionBibliograficaService._list_query(filters)
        total = query.count()
        return [d.serialize() for d in query.offset((page - 1) * per_page).limit(per_page).all()], total

    # =========================
    # GET BY ID
    # =========================
    @staticmethod
    def get_by_id(doc_id: int):
        doc = db.session.get(DocumentacionBibliografica, doc_id)
        if not doc:
            raise NotFoundError("Documentacion bibliografica no encontrada")
        return doc.serialize()

    @staticmethod
    def get_historial(doc_id: int):
        doc = db.session.get(DocumentacionBibliografica, doc_id)
        if not doc:
            raise NotFoundError("Documentacion bibliografica no encontrada")
        return AuditoriaService.obtener_historial_entidad(
            entidad="documentacion_bibliografica",
            registro_id=doc.id,
            extra_filter=or_(
                AuditoriaCampo.campo.in_(DOCUMENTACION_HISTORY_FIELDS),
                (AuditoriaCampo.campo == "autores") &
                (AuditoriaCampo.valor_nuevo["accion"].as_string().in_(("vincular", "desvincular"))),
            ),
        )

    # =========================
    # CREATE
    # =========================
    @staticmethod
    def create(data: dict, user_id: int):
        if not isinstance(data, dict):
            raise ValidationError("Envíe los datos de la documentación e intente nuevamente.")
        grupo = db.session.get(GrupoInvestigacionUtn, data.get("grupo_id"))
        if not grupo or grupo.deleted_at is not None:
            raise NotFoundError("El grupo ya no está disponible. Recargue el formulario e intente nuevamente.")
        fields = {key: f"Ingrese {label} de la documentación." for key, label in (("titulo", "el título"), ("editorial", "la editorial")) if not isinstance(data.get(key), str) or not data[key].strip()}
        if fields:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": fields})

        if not isinstance(data.get("anio"), int):
            raise ValidationError("Revise el año e intente nuevamente.", details={"fields": {"anio": "Ingrese un año válido."}})

        doc = DocumentacionBibliografica(
            titulo=DocumentacionBibliograficaService._normalizar_texto(
                data["titulo"], "Titulo"
            ),
            editorial=DocumentacionBibliograficaService._normalizar_texto(
                data["editorial"], "Editorial"
            ),
            anio=data["anio"],
            fecha=DocumentacionBibliograficaService._parse_fecha(data.get("fecha")),
            grupo_id=data["grupo_id"],
            created_by=user_id
        )

        db.session.add(doc)
        db.session.commit()

        return doc.serialize()

    # =========================
    # UPDATE
    # =========================
    @staticmethod
    def update(doc_id: int, data: dict, user_id: int):
        doc = DocumentacionBibliograficaService._get_activo_or_404(doc_id)
        cambios = {}

        if "titulo" in data:
            nuevo_valor = DocumentacionBibliograficaService._normalizar_texto(
                data["titulo"], "Titulo"
            )
            cambio = AuditoriaService.construir_cambio(doc.titulo, nuevo_valor)
            if cambio:
                cambios["titulo"] = cambio
                doc.titulo = nuevo_valor

        if "editorial" in data:
            nuevo_valor = DocumentacionBibliograficaService._normalizar_texto(
                data["editorial"], "Editorial"
            )
            cambio = AuditoriaService.construir_cambio(doc.editorial, nuevo_valor)
            if cambio:
                cambios["editorial"] = cambio
                doc.editorial = nuevo_valor

        if "anio" in data:
            cambio = AuditoriaService.construir_cambio(doc.anio, data["anio"])
            if cambio:
                cambios["anio"] = cambio
                doc.anio = data["anio"]

        if "fecha" in data:
            nuevo_valor = DocumentacionBibliograficaService._parse_fecha(
                data["fecha"]
            )
            cambio = AuditoriaService.construir_cambio(doc.fecha, nuevo_valor)
            if cambio:
                cambios["fecha"] = cambio
                doc.fecha = nuevo_valor

        if "grupo_id" in data:
            cambio = AuditoriaService.construir_cambio(doc.grupo_id, data["grupo_id"])
            if cambio:
                cambios["grupo_id"] = cambio
                doc.grupo_id = data["grupo_id"]

        if cambios:
            doc.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="documentacion_bibliografica",
                registro_id=doc.id,
                cambios=cambios,
                user_id=user_id
            )

        db.session.commit()

        return doc.serialize()

    # =========================
    # SOFT DELETE
    # =========================
    @staticmethod
    def delete(doc_id: int, user_id: int):
        doc = DocumentacionBibliograficaService._get_activo_or_404(doc_id)

        doc.soft_delete(user_id)

        db.session.commit()

        return {"message": "Documentacion bibliografica eliminada correctamente"}

    # =========================
    # RELACION DOCUMENTO - AUTOR
    # =========================
    @staticmethod
    def add_autor(doc_id: int, autor_id: int, user_id: int):
        doc = DocumentacionBibliograficaService._get_activo_or_404(doc_id)

        autor = db.session.get(Autor, autor_id)
        if not autor or getattr(autor, "deleted_at", None) is not None:
            raise NotFoundError("Autor no encontrado")

        if autor in doc.autores:
            raise ConflictError("El autor ya esta asociado")

        doc.autores.append(autor)
        doc.mark_updated(user_id)
        AuditoriaService.registrar_evento_relacion(
            entidad="documentacion_bibliografica", registro_id=doc.id,
            relacion="autores", accion="vincular",
            detalle={"nombre_apellido": autor.nombre_apellido}, user_id=user_id,
        )
        db.session.commit()

        return doc.serialize()

    @staticmethod
    def remove_autor(doc_id: int, autor_id: int, user_id: int):
        doc = DocumentacionBibliograficaService._get_activo_or_404(doc_id)

        autor = db.session.get(Autor, autor_id)
        if not autor:
            raise NotFoundError("Autor no encontrado")

        if autor not in doc.autores:
            raise NotFoundError("La relacion no existe")

        doc.autores.remove(autor)
        doc.mark_updated(user_id)
        AuditoriaService.registrar_evento_relacion(
            entidad="documentacion_bibliografica", registro_id=doc.id,
            relacion="autores", accion="desvincular",
            detalle={"nombre_apellido": autor.nombre_apellido}, user_id=user_id,
        )
        db.session.commit()

        return doc.serialize()

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        documentos = consultar_entidades_memoria(DocumentacionBibliografica, memoria_version, campo_grupo="grupo_id")

        snapshots = []
        for doc in documentos:
            if not registro_puntual_en_memoria(memoria_version, doc, doc.fecha):
                continue
            snapshot = DocumentacionBibliograficaMemoriaVersion(
                memoria_version_id=memoria_version.id,
                documentacion_bibliografica_id=doc.id,
                titulo=doc.titulo,
                editorial=doc.editorial,
                anio=doc.anio,
                fecha=doc.fecha,
                grupo_id=doc.grupo_id,
                grupo_nombre=(
                    doc.grupo_utn.nombre_unidad_academica
                    if doc.grupo_utn else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            db.session.flush()

            for autor in getattr(doc, "autores", []):
                if not registro_puntual_en_memoria(memoria_version, autor, doc.fecha):
                    continue

                autor_snapshot = DocumentacionBibliograficaAutorMemoriaVersion(
                    documentacion_memoria_version=snapshot,
                    autor_id=autor.id,
                    nombre_apellido=autor.nombre_apellido,
                    created_by=user_id
                )
                db.session.add(autor_snapshot)

            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            DocumentacionBibliograficaMemoriaVersion.query
            .filter(
                DocumentacionBibliograficaMemoriaVersion.memoria_version_id == memoria_version_id,
                DocumentacionBibliograficaMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(DocumentacionBibliograficaMemoriaVersion.titulo.asc())
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
