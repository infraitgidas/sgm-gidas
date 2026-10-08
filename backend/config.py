import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(os.path.join(basedir, env_file))


def _env_or_file(name: str) -> str | None:
    direct_value = os.getenv(name)
    file_path = os.getenv(f"{name}_FILE")

    if direct_value is not None and direct_value.strip() != "":
        return direct_value
    if not file_path:
        return None

    try:
        value = Path(file_path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer {name}_FILE") from exc

    if not value:
        raise RuntimeError(f"{name}_FILE no puede estar vacio")
    return value


def _parse_csv_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_insecure_secret(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    insecure_values = {
        "change-me",
        "changeme",
        "replace-with-secure-secret",
        "secret",
        "dev-secret",
        "test-secret",
    }
    return normalized in insecure_values or len(value.strip()) < 32


def _validate_cors_origins(origins: list[str]) -> None:
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path != ""
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(
                "CORS_ORIGINS debe contener origenes HTTPS sin rutas, credenciales, "
                "query ni fragmentos"
            )


def _parse_int_env_range(
    name: str,
    default: int,
    min_value: int,
    max_value: int,
    unit: str = "minutos",
) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un numero entero") from exc

    if value < min_value or value > max_value:
        raise RuntimeError(
            f"{name} debe estar entre {min_value} y {max_value} {unit}"
        )

    return value


def _require_production_security(config_class):
    if config_class.APP_ENV not in {"production", "prod"}:
        return

    required_secrets = {
        "SECRET_KEY": config_class.SECRET_KEY,
        "JWT_SECRET": config_class.JWT_SECRET,
        "REFRESH_SECRET": config_class.REFRESH_SECRET,
    }
    missing_or_insecure = [
        key for key, value in required_secrets.items() if _is_insecure_secret(value)
    ]

    if missing_or_insecure:
        raise RuntimeError(
            "Configuracion insegura para produccion. Revise: "
            + ", ".join(missing_or_insecure)
        )

    secret_values = list(required_secrets.values())
    if len(set(secret_values)) != len(secret_values):
        raise RuntimeError(
            "SECRET_KEY, JWT_SECRET y REFRESH_SECRET deben ser independientes"
        )

    if config_class.CORS_ORIGINS == "*" or "*" in config_class.CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS no puede usar '*' en produccion")

    _validate_cors_origins(config_class.CORS_ORIGINS)

    if config_class.RATELIMIT_STORAGE_URI.strip().lower() == "memory://":
        raise RuntimeError(
            "RATELIMIT_STORAGE_URI debe usar almacenamiento compartido en produccion"
        )

    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL es obligatorio en produccion")


class Config:
    APP_ENV = os.getenv("APP_ENV", "local")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json" if APP_ENV in {"production", "prod"} else "text")
    SERVICE_NAME = os.getenv("SERVICE_NAME", "gidas-backend")
    APP_VERSION = os.getenv("APP_VERSION", "development")
    SECRET_KEY = _env_or_file("SECRET_KEY") or secrets.token_urlsafe(48)
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    FRONTEND_URLS = _parse_csv_env(os.getenv("FRONTEND_URLS")) or [FRONTEND_URL]
    CORS_ORIGINS = FRONTEND_URLS
    MAX_CONTENT_LENGTH = _parse_int_env_range(
        "MAX_CONTENT_LENGTH",
        default=10 * 1024 * 1024,
        min_value=1024,
        max_value=20 * 1024 * 1024,
        unit="bytes",
    )
    MAX_JSON_CONTENT_LENGTH = _parse_int_env_range(
        "MAX_JSON_CONTENT_LENGTH",
        default=1024 * 1024,
        min_value=1024,
        max_value=MAX_CONTENT_LENGTH,
        unit="bytes",
    )

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/gidas_db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False") == "True"

    JWT_SECRET = _env_or_file("JWT_SECRET") or SECRET_KEY
    REFRESH_SECRET = _env_or_file("REFRESH_SECRET") or SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = os.getenv("JWT_ISSUER", "auth-service")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE") or None
    JWT_EXPIRATION_MINUTES = _parse_int_env_range(
        "JWT_EXPIRATION_MINUTES",
        default=15,
        min_value=5,
        max_value=1440,
    )
    REFRESH_TOKEN_EXPIRATION_MINUTES = _parse_int_env_range(
        "REFRESH_TOKEN_EXPIRATION_MINUTES",
        default=10080,
        min_value=60,
        max_value=43200,
    )
    SESSION_WARNING_SECONDS = _parse_int_env_range(
        "SESSION_WARNING_SECONDS",
        default=300,
        min_value=30,
        max_value=3600,
    )
    REFRESH_SESSION_RETENTION_DAYS = _parse_int_env_range(
        "REFRESH_SESSION_RETENTION_DAYS",
        default=30,
        min_value=1,
        max_value=365,
        unit="dias",
    )
    REFRESH_COOKIE_NAME = "gidas_refresh"
    REFRESH_COOKIE_PATH = "/api/v1/auth"
    REFRESH_COOKIE_HTTPONLY = True
    REFRESH_COOKIE_SAMESITE = "Lax"
    REFRESH_COOKIE_SECURE = APP_ENV in {"production", "prod"}
    HSTS_ENABLED = os.getenv("HSTS_ENABLED", "False") == "True"
    HSTS_MAX_AGE = _parse_int_env_range(
        "HSTS_MAX_AGE",
        default=31536000,
        min_value=0,
        max_value=63072000,
        unit="segundos",
    )
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "120 per minute")
    RATELIMIT_HEADERS_ENABLED = os.getenv("RATELIMIT_HEADERS_ENABLED", "True") == "True"

    AUTH_LOGIN_LIMIT = os.getenv("AUTH_LOGIN_LIMIT", "10 per minute")
    AUTH_REFRESH_LIMIT = os.getenv("AUTH_REFRESH_LIMIT", "30 per minute")
    AUTH_REGISTER_LIMIT = os.getenv("AUTH_REGISTER_LIMIT", "5 per hour")
    AUTH_CHANGE_PASSWORD_LIMIT = os.getenv("AUTH_CHANGE_PASSWORD_LIMIT", "10 per hour")
    EXPORT_LIMIT = os.getenv("EXPORT_LIMIT", "10 per hour")
    SEARCH_LIMIT = os.getenv("SEARCH_LIMIT", "90 per minute")
    SEARCH_MAX_QUERY_LENGTH = _parse_int_env_range(
        "SEARCH_MAX_QUERY_LENGTH",
        default=80,
        min_value=10,
        max_value=200,
    )
    SEARCH_MAX_PER_PAGE = _parse_int_env_range(
        "SEARCH_MAX_PER_PAGE",
        default=50,
        min_value=9,
        max_value=100,
    )
    SEARCH_MAX_SCAN_PER_MODEL = _parse_int_env_range(
        "SEARCH_MAX_SCAN_PER_MODEL",
        default=300,
        min_value=50,
        max_value=1000,
    )
    PAGINATION_DEFAULT_PER_PAGE = _parse_int_env_range(
        "PAGINATION_DEFAULT_PER_PAGE",
        default=9,
        min_value=1,
        max_value=100,
    )
    PAGINATION_MAX_PER_PAGE = _parse_int_env_range(
        "PAGINATION_MAX_PER_PAGE",
        default=100,
        min_value=9,
        max_value=500,
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"


class DevelopmentConfig(Config):
    DEBUG = True
    CORS_ORIGINS = "*"

class DockerConfig(Config):
    DEBUG = os.getenv("FLASK_DEBUG", "False") == "True"

class StagingConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    DEBUG = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REFRESH_COOKIE_SECURE = True


CONFIG_BY_ENV = {
    "local": DevelopmentConfig,
    "development": DevelopmentConfig,
    "docker": DockerConfig,
    "staging": StagingConfig,
    "preproduction": StagingConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def get_config_class():
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    config_class = CONFIG_BY_ENV.get(app_env, DevelopmentConfig)
    _require_production_security(config_class)
    return config_class
