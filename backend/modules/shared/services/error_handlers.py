from flask import g
from werkzeug.exceptions import HTTPException

from modules.shared.controllers.responses import error_response, exception_response
from modules.shared.exceptions import DomainError
from modules.shared.services.logging_config import get_logger


logger = get_logger("gidas.error")

HTTP_ERROR_CODES = {
    400: "VALIDATION_ERROR",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "REQUEST_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _request_details() -> dict:
    request_id = getattr(g, "request_id", None)
    return {"request_id": request_id} if request_id else {}


def register_error_handlers(app):
    @app.errorhandler(DomainError)
    def _domain_exception(error):
        return exception_response(error, operation="procesar solicitud")

    @app.errorhandler(HTTPException)
    def _http_exception(error):
        status_code = error.code or 500
        return error_response(
            HTTP_ERROR_CODES.get(status_code, "HTTP_ERROR"),
            details=_request_details(),
            status_code=status_code,
        )

    @app.errorhandler(Exception)
    def _unhandled_exception(error):
        logger.exception("unhandled exception type=%s request_id=%s", type(error).__name__, getattr(g, "request_id", None))
        return error_response(
            "INTERNAL_ERROR",
            details=_request_details(),
            status_code=500,
        )

    return app
