"""Domain-specific exceptions.

The service layer raises these. The API layer catches them and translates
to appropriate HTTP status codes. This keeps HTTP concerns out of the
service layer (separation of concerns).
"""


class AppException(Exception):
    """Base class for all app-specific exceptions."""

    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = 404
    detail = "Resource not found"


class ForbiddenError(AppException):
    status_code = 403
    detail = "You do not have permission to perform this action"


class ConflictError(AppException):
    status_code = 409
    detail = "Conflict with current state"


class ValidationError(AppException):
    status_code = 422
    detail = "Validation failed"


class AuthenticationError(AppException):
    status_code = 401
    detail = "Authentication required"