from flask import Blueprint

from modules.shared.controllers.form_draft_controller import FormDraftController
from modules.shared.services.middleware import requiere_rol


form_draft_bp = Blueprint("form_draft", __name__, url_prefix="/borradores")


@form_draft_bp.get("")
@requiere_rol("ADMIN", "GESTOR")
def list_all():
    return FormDraftController.list_all()


@form_draft_bp.get("/<module>/<record_key>")
@requiere_rol("ADMIN", "GESTOR")
def get(module, record_key):
    return FormDraftController.get(module, record_key)


@form_draft_bp.put("/<module>/<record_key>")
@requiere_rol("ADMIN", "GESTOR")
def save(module, record_key):
    return FormDraftController.save(module, record_key)


@form_draft_bp.delete("/<module>/<record_key>")
@requiere_rol("ADMIN", "GESTOR")
def delete(module, record_key):
    return FormDraftController.delete(module, record_key)
