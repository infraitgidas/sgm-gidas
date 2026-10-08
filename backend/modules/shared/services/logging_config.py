import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone

from flask import g, has_request_context, request


TEXT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s"
SENSITIVE_PATTERN = re.compile(
    r'''(?ix)
    (["']?(?:authorization|password|contrasena|contraseña|token|access_token|
    refresh_token|secret|api_key|cookie|set-cookie)["']?\s*[:=]\s*)
    (?:"[^"]*"|'[^']*'|[^\s,;}]+)
    '''
)
BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)([^\s,;]+)")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def redact_sensitive(value: str) -> str:
    redacted = SENSITIVE_PATTERN.sub(
        lambda match: f"{match.group(1)}[REDACTED]", value
    )
    return BEARER_PATTERN.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)


class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact_sensitive(str(record.msg))
        if record.args:
            redact = lambda value: redact_sensitive(value) if isinstance(value, str) else value
            if isinstance(record.args, dict):
                record.args = {key: redact(value) for key, value in record.args.items()}
            else:
                record.args = tuple(redact(value) for value in record.args)
        return True


class SafeTextFormatter(logging.Formatter):
    def formatException(self, exc_info):
        return redact_sensitive(super().formatException(exc_info))


class JsonFormatter(logging.Formatter):
    def __init__(self, service="gidas-backend", environment="local", version="development"):
        super().__init__()
        self.service = service
        self.environment = environment
        self.version = version
        self.include_exception_details = environment not in {"production", "prod"}

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "environment": self.environment,
            "version": self.version,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if has_request_context():
            payload.update({
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "user_id": getattr(g, "current_user_id", None),
                "role": getattr(g, "current_user_rol", None),
            })
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
            if self.include_exception_details:
                payload["exception"] = redact_sensitive(
                    self.formatException(record.exc_info)
                )
        return json.dumps(payload, ensure_ascii=False, default=str)


def resolve_log_level(raw_level):
    return getattr(logging, (raw_level or "INFO").strip().upper(), logging.INFO)


def get_logger(name):
    return logging.getLogger(name)


def configure_logging(app_env="local", log_level="INFO", log_format="text", service="gidas-backend", version="development"):
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(resolve_log_level(log_level))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(service, app_env, version)
        if log_format == "json" else SafeTextFormatter(TEXT_LOG_FORMAT)
    )
    handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(handler)
    if app_env in {"production", "prod"}:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return root_logger


def register_request_logging(app):
    request_logger = logging.getLogger("gidas.request")

    @app.before_request
    def _start_request():
        incoming = request.headers.get("X-Request-ID", "").strip()
        g.request_id = (
            incoming if REQUEST_ID_PATTERN.fullmatch(incoming) else str(uuid.uuid4())
        )
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _log_request(response):
        started_at = getattr(g, "request_started_at", time.perf_counter())
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        request_logger.info(
            "request method=%s path=%s endpoint=%s status=%s duration_ms=%s request_id=%s",
            request.method, request.path, request.endpoint,
            response.status_code, duration_ms, request_id,
        )
        return response

    return app
