"""Global exception handlers registered on the FastAPI app.

Handler priority (top = highest):
  1. AppException       → structured error from any service/utility layer.
  2. HTTPException      → raised by FastAPI internals (auth scheme, 405, etc.).
  3. RequestValidationError → Pydantic body/query/path validation failures.
  4. Exception          → catch-all safety net for unhandled errors.

All handlers return the standard APIResponse envelope so the client always
gets { success, status_code, message, data, error }.
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the given FastAPI instance."""

    # ------------------------------------------------------------------ #
    # 1. AppException — our own typed exceptions from the service layer   #
    # ------------------------------------------------------------------ #
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "AppException on %s %s | %s", request.method, request.url.path, exc.message
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "status_code": exc.status_code,
                "message": exc.message,
                "data": None,
                "error": exc.error,
            },
        )

    # ------------------------------------------------------------------ #
    # 2. HTTPException — FastAPI / Starlette built-in errors             #
    # ------------------------------------------------------------------ #
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "status_code": exc.status_code,
                "message": message,
                "data": None,
                "error": message,
            },
        )

    # ------------------------------------------------------------------ #
    # 3. RequestValidationError — Pydantic schema validation failures     #
    # ------------------------------------------------------------------ #
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": "Validation failed. Please check your input.",
                "data": None,
                "error": errors,
            },
        )

    # ------------------------------------------------------------------ #
    # 4. Exception — unhandled catch-all (never leak stack traces)        #
    # ------------------------------------------------------------------ #
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "An unexpected error occurred. Please try again later.",
                "data": None,
                "error": "INTERNAL_SERVER_ERROR",
            },
        )
