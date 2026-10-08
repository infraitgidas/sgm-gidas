from modules.produccion.models.documentacion_autores import Autor, DocumentacionBibliografica
from extension import db
from modules.shared.services.text_validation import has_only_letters_and_spaces
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.catalog_pagination import catalog_page


class AutorService:

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc"):
        return catalog_page(Autor, Autor.nombre_apellido, activos=activos, orden=orden, page=page, per_page=per_page)

    # =========================
    # Helpers
    # =========================

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or valor <= 0:
            raise ValidationError(f"El campo '{campo}' debe ser un entero positivo")
        return valor

    @staticmethod
    def _validar_nombre(nombre: str):
        if not nombre or not isinstance(nombre, str) or not nombre.strip():
            raise ValidationError("El nombre es obligatorio")
        if not has_only_letters_and_spaces(nombre):
            raise ValidationError("Use solo letras y espacios en el nombre", details={"fields": {"nombre_apellido": "Use solo letras y espacios en el nombre"}})
        return " ".join(nombre.split())

    @staticmethod
    def _get_or_404(autor_id: int):
        autor = db.session.get(Autor, AutorService._validar_id(autor_id, "autor_id"))
        if not autor:
            raise NotFoundError("Autor no encontrado")
        return autor

    # =========================
    # CRUD
    # =========================

    @staticmethod
    def get_all(activos: str = "true"):
        query = Autor.query
        if activos == "false":
            query = query.filter(Autor.deleted_at.isnot(None))
        elif activos != "all":
            query = query.filter(Autor.deleted_at.is_(None))
        autores = query.order_by(Autor.nombre_apellido.asc()).all()
        return [a.serialize() for a in autores]

    @staticmethod
    def get_by_id(autor_id: int):
        autor = AutorService._get_or_404(autor_id)
        return autor.serialize()

    @staticmethod
    def get_historial(autor_id: int):
        autor = AutorService._get_or_404(autor_id)
        return AuditoriaService.obtener_historial_entidad("autor", autor.id)

    @staticmethod
    def create(data: dict, user_id: int | None = None):
        AutorService._validar_payload(data)
        nombre = AutorService._validar_nombre(data.get("nombre_apellido"))

        existente = (
            Autor.query
            .filter(db.func.lower(Autor.nombre_apellido) == nombre.lower())
            .first()
        )

        if existente:
            raise ConflictError("Ya existe un autor con ese nombre")

        autor = Autor(nombre_apellido=nombre, created_by=user_id)

        db.session.add(autor)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return autor.serialize()

    @staticmethod
    def update(autor_id: int, data: dict, user_id: int | None = None):
        AutorService._validar_payload(data)
        autor = AutorService._get_or_404(autor_id)
        if autor.deleted_at is not None:
            raise ConflictError("No se puede editar un autor inactivo")

        if "nombre_apellido" in data:
            nombre = AutorService._validar_nombre(data["nombre_apellido"])
            cambio = AuditoriaService.construir_cambio(autor.nombre_apellido, nombre)
            if cambio:
                existente = (
                    Autor.query
                    .filter(
                        db.func.lower(Autor.nombre_apellido) == nombre.lower(),
                        Autor.id != autor.id,
                    )
                    .first()
                )
                if existente:
                    raise ConflictError("Ya existe un autor con ese nombre")
                autor.nombre_apellido = nombre
                autor.mark_updated(user_id)
                AuditoriaService.registrar_cambios(
                    "autor", autor.id, {"nombre_apellido": cambio}, user_id=user_id
                )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return autor.serialize()

    @staticmethod
    def delete(autor_id: int, user_id: int | None = None):
        autor = AutorService._get_or_404(autor_id)
        if autor.deleted_at is not None:
            raise ConflictError("El autor ya está inactivo")

        tiene_documentacion_activa = db.session.query(Autor.id).filter(
            Autor.id == autor.id,
            Autor.libros.any(DocumentacionBibliografica.deleted_at.is_(None)),
        ).first()
        if tiene_documentacion_activa:
            raise ConflictError("No se puede eliminar un autor con documentaciones activas asociadas")

        autor.soft_delete(user_id)
        AuditoriaService.registrar_cambios(
            "autor", autor.id,
            {"activo": AuditoriaService.construir_cambio(True, False)},
            user_id=user_id,
        )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Autor eliminado correctamente"}

    # =========================
    # RELACION AUTOR - LIBRO
    # =========================

    @staticmethod
    def add_libro(autor_id: int, libro_id: int, user_id: int | None = None):
        autor = AutorService._get_or_404(autor_id)
        from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService
        DocumentacionBibliograficaService.add_autor(
            AutorService._validar_id(libro_id, "libro_id"), autor.id, user_id
        )
        return autor.serialize()

    @staticmethod
    def remove_libro(autor_id: int, libro_id: int, user_id: int | None = None):
        autor = AutorService._get_or_404(autor_id)
        from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService
        DocumentacionBibliograficaService.remove_autor(
            AutorService._validar_id(libro_id, "libro_id"), autor.id, user_id
        )
        return autor.serialize()
