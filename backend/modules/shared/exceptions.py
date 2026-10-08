class DomainError(Exception):
    code = "DOMAIN_ERROR"
    status_code = 400

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError, ValueError):
    code = "VALIDATION_ERROR"
    status_code = 400


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(DomainError):
    code = "CONFLICT"
    status_code = 409


class ForbiddenError(DomainError):
    code = "FORBIDDEN"
    status_code = 403


class AuthenticationError(DomainError):
    code = "AUTH_REQUIRED"
    status_code = 401


class LoginLockedError(DomainError):
    code = "LOGIN_LOCKED"
    status_code = 429

    def __init__(self, retry_after_seconds: int):
        remaining_minutes = max(1, (retry_after_seconds + 59) // 60)
        unit = "minuto" if remaining_minutes == 1 else "minutos"
        super().__init__(
            f"Lo sentimos, se alcanzó el límite de intentos. Intente nuevamente en {remaining_minutes} {unit}."
        )
        self.retry_after_seconds = retry_after_seconds
