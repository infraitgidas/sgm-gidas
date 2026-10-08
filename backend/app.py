from flask import Flask, request
from extension import db, migrate, limiter
from flask_cors import CORS
from config import get_config_class
from modules import blueprints
from modules import models_registry  # noqa: F401
from werkzeug.middleware.proxy_fix import ProxyFix
from modules.shared.routes.versioning import (
    register_api_version_header,
    register_blueprints,
)
from modules.shared.services.error_handlers import register_error_handlers
from modules.shared.services.logging_config import (
    configure_logging,
    get_logger,
    register_request_logging,
)
from modules.shared.services.request_security import register_request_body_security
from modules.auth.commands.refresh_sessions import register_refresh_session_commands
from modules.shared.services.tenant_request import register_tenant_request_scope
from modules.shared.services.tenant_scope import register_tenant_orm_policy


logger = get_logger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config_class())
    configure_logging(
        app.config["APP_ENV"], app.config["LOG_LEVEL"],
        app.config["LOG_FORMAT"], app.config["SERVICE_NAME"],
        app.config["APP_VERSION"],
    )
    register_request_logging(app)
    register_request_body_security(app)
    register_error_handlers(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    CORS(
        app,
        resources={r"/*": {
            "origins": app.config["CORS_ORIGINS"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }},
        supports_credentials=True,
        always_send=False,
    )

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)


    register_blueprints(app, blueprints)
    register_api_version_header(app)
    register_tenant_orm_policy()
    register_tenant_request_scope(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'",
        )
        response.headers.setdefault("Cache-Control", "private, no-store")
        if app.config["HSTS_ENABLED"] and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={app.config['HSTS_MAX_AGE']}; includeSubDomains",
            )
        return response

    register_refresh_session_commands(app)

    logger.info("Aplicación inicializada. Usa 'flask db upgrade' para crear/migrar tablas.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
