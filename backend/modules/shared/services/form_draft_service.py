import json
import math
import re
from datetime import datetime, timedelta

from extension import db
from sqlalchemy.exc import IntegrityError
from modules.shared.exceptions import NotFoundError, ValidationError
from modules.shared.models.form_draft import FormDraft


RETENTION = timedelta(days=7)
MAX_BYTES = 65536
SENSITIVE_KEY = re.compile(r"token|password|contrasena|contraseña|secret|credential|authorization|cookie|clave", re.I)
MODULES = {
    "personal-personal": ("Personal", "/personal/nuevo?tipo=PERSONAL", "/personal/personal/{id}/editar"),
    "personal-becario": ("Becario", "/personal/nuevo?tipo=BECARIO", "/personal/becario/{id}/editar"),
    "personal-investigador": ("Investigador", "/personal/nuevo?tipo=INVESTIGADOR", "/personal/investigador/{id}/editar"),
    "grupo-uct": ("UCT", "/uct/nueva", "/uct/nueva"),
    "proyectos": ("Proyecto", "/proyectos/nuevo", "/proyectos/{id}/editar"),
    "recursos-erogaciones": ("Movimiento", "/movimientos/nuevo", "/movimientos/{id}/editar"),
    "recursos-equipamiento": ("Equipamiento", "/equipamiento/nuevo", "/equipamiento/{id}/editar"),
    "transferencia": ("Transferencia", "/transferencias/nuevo", "/transferencias/{id}/editar"),
    "memorias": ("Memoria", "/memorias/nueva", "/memorias/nueva"),
    "grupo-visitantes": ("Visita académica", "/visitantes/nuevo", "/visitantes/{id}/editar"),
    "proyectos-participaciones": ("Participación", "/participaciones/nuevo", "/participaciones/{id}/editar"),
    "produccion-registros": ("Registro de propiedad", "/registros-propiedad/nuevo", "/registros-propiedad/{id}/editar"),
    "produccion-documentacion": ("Documentación", "/documentacion/nuevo", "/documentacion/{id}/editar"),
    "produccion-articulos": ("Artículo de divulgación", "/articulos-divulgacion/nuevo", "/articulos-divulgacion/{id}/editar"),
    "produccion-distinciones": ("Distinción", "/distinciones/nuevo", "/distinciones/{id}/editar"),
    "produccion-docencia": ("Docencia", "/docenciaInvestigador/nuevo", "/docenciaInvestigador/{id}/editar"),
    "produccion-reuniones": ("Trabajo en reunión", "/trabajos-reunion/nuevo", "/trabajos-reunion/{id}/editar"),
    "produccion-revistas": ("Trabajo en revista", "/trabajos-revistas/nuevo", "/trabajos-revistas/{id}/editar"),
}

DISPLAY_FIELDS = {
    "grupo-uct": ("data.nombreSigla", "data.facultadRegional"),
    "grupo-visitantes": ("razon", "procedencia"),
    "proyectos": ("nombreProyecto", "codigoProyecto"),
    "proyectos-participaciones": ("nombreEvento",),
    "recursos-erogaciones": ("numeroErogacion",),
    "recursos-equipamiento": ("denominacion",),
    "transferencia": ("data.denominacion", "data.numeroTransferencia"),
    "memorias": ("periodoInicio", "periodoFin"),
    "produccion-registros": ("nombre_articulo",),
    "produccion-documentacion": ("data.titulo",),
    "produccion-articulos": ("titulo",),
    "produccion-distinciones": ("descripcion",),
    "produccion-docencia": ("curso", "institucion"),
    "produccion-reuniones": ("titulo", "nombreReunion"),
    "produccion-revistas": ("titulo", "nombreRevista"),
}


def _validate_target(module, record_key):
    if module not in MODULES or not re.fullmatch(r"new|[1-9][0-9]{0,11}", record_key):
        raise ValidationError("Seleccione un formulario disponible.")


def _validate_data(value, depth=0):
    if depth > 12:
        raise ValidationError("El borrador es demasiado complejo. Revise los datos e intente nuevamente.")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or SENSITIVE_KEY.search(key):
                raise ValidationError("El borrador contiene un campo que no se puede guardar.")
            _validate_data(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_data(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("Revise los datos del borrador e intente nuevamente.")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValidationError("Revise los datos del borrador e intente nuevamente.")


def _display_name(module, data):
    if not isinstance(data, dict):
        return None
    fields = data.get("fields", data)
    if not isinstance(fields, dict):
        return None
    if module.startswith("personal-"):
        raw_name = fields.get("nombreApellido")
        if isinstance(raw_name, str):
            words = raw_name.split()
            if words and all(word.isalpha() for word in words):
                return " ".join(words)[:120]
        return None
    for path in DISPLAY_FIELDS.get(module, ()):
        value = fields
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            cleaned = " ".join(str(value).split())[:120]
            if cleaned:
                return cleaned
    return None


def _serialize(row, include_data=False):
    label, new_path, edit_path = MODULES[row.module]
    path = new_path if row.record_key == "new" else edit_path.format(id=row.record_key)
    result = {
        "module": row.module,
        "record_key": row.record_key,
        "label": label,
        "path": path,
        "saved_at": row.saved_at.isoformat() + "Z",
        "expires_at": row.expires_at.isoformat() + "Z",
    }
    display_name = _display_name(row.module, row.data)
    if display_name:
        result["display_name"] = display_name
    if include_data:
        result["data"] = row.data
    return result


class FormDraftService:
    @staticmethod
    def _purge_expired(user_id, now):
        deleted = FormDraft.query.filter_by(user_id=user_id).filter(FormDraft.expires_at <= now).delete(synchronize_session=False)
        if deleted:
            db.session.commit()

    @staticmethod
    def list_for_user(user_id, page=None, per_page=None):
        now = datetime.utcnow()
        FormDraftService._purge_expired(user_id, now)
        query = FormDraft.query.filter_by(user_id=user_id).filter(FormDraft.expires_at > now)
        total = query.count() if page is not None else None
        query = query.order_by(FormDraft.saved_at.desc(), FormDraft.id.desc())
        if page is not None:
            query = query.offset((page - 1) * per_page).limit(per_page)
        data = [_serialize(row) for row in query.all()]
        return (data, total) if page is not None else data

    @staticmethod
    def get(user_id, module, record_key):
        _validate_target(module, record_key)
        row = FormDraft.query.filter_by(user_id=user_id, module=module, record_key=record_key).first()
        if row is not None and row.expires_at <= datetime.utcnow():
            db.session.delete(row)
            db.session.commit()
            row = None
        if row is None:
            raise NotFoundError("No encontramos un borrador vigente para este formulario.")
        return _serialize(row, include_data=True)

    @staticmethod
    def save(user_id, module, record_key, data):
        _validate_target(module, record_key)
        if not isinstance(data, dict):
            raise ValidationError("Revise los datos del borrador e intente nuevamente.")
        _validate_data(data)
        if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
            raise ValidationError("El borrador supera el tamaño permitido. Reduzca el contenido e intente nuevamente.")
        now = datetime.utcnow()
        FormDraftService._purge_expired(user_id, now)
        row = FormDraft.query.filter_by(user_id=user_id, module=module, record_key=record_key).first()
        created = row is None
        if row is None:
            row = FormDraft(user_id=user_id, module=module, record_key=record_key)
            db.session.add(row)
        row.data = data
        row.saved_at = now
        row.expires_at = now + RETENTION
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if not created:
                raise
            row = FormDraft.query.filter_by(user_id=user_id, module=module, record_key=record_key).first()
            if row is None:
                raise
            row.data = data
            row.saved_at = now
            row.expires_at = now + RETENTION
            db.session.commit()
        return _serialize(row)

    @staticmethod
    def delete(user_id, module, record_key):
        _validate_target(module, record_key)
        row = FormDraft.query.filter_by(user_id=user_id, module=module, record_key=record_key).first()
        if row:
            db.session.delete(row)
            db.session.commit()
