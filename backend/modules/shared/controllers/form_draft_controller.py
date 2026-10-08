from flask import g, request

from modules.shared.controllers.responses import error_response, paginated_response, success_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.services.form_draft_service import FormDraftService


class FormDraftController:
    @staticmethod
    def list_all():
        if pagination_requested(request.args):
            try:
                params = parse_pagination_params(request.args)
            except ValueError as exc:
                return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
            data, total = FormDraftService.list_for_user(g.current_user_id, params["page"], params["per_page"])
            return paginated_response(data, params["page"], params["per_page"], total)
        return success_response(FormDraftService.list_for_user(g.current_user_id))

    @staticmethod
    def get(module, record_key):
        return success_response(FormDraftService.get(g.current_user_id, module, record_key))

    @staticmethod
    def save(module, record_key):
        body = request.get_json(silent=True)
        data = body.get("data") if isinstance(body, dict) else None
        return success_response(FormDraftService.save(g.current_user_id, module, record_key, data))

    @staticmethod
    def delete(module, record_key):
        FormDraftService.delete(g.current_user_id, module, record_key)
        return success_response({"deleted": True})
