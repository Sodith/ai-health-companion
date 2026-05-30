"""Custom application exceptions.

Instead of raising raw ValueError or HTTPException across the codebase,
every layer raises AppException with a descriptive message and HTTP status.

The global exception handler in middleware/exception_middleware.py catches
these and formats them into the standard APIResponse envelope automatically.

Usage:
    raise AppException(status_code=409, message="Email already registered.")
"""

from fastapi import status


class AppException(Exception):
    """Base application exception carrying an HTTP status code and message.

    Raise this from any service or utility. The exception middleware will
    catch it and return a properly formatted APIResponse to the client.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error = error or self._default_error_code(status_code)

    @staticmethod
    def _default_error_code(status_code: int) -> str:
        _map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "INTERNAL_SERVER_ERROR",
        }
        return _map.get(status_code, "ERROR")


# ---------------------------------------------------------------------------
# Convenience sub-classes — use these for clarity at the call site
# ---------------------------------------------------------------------------

class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request.") -> None:
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied.") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists.") -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)

