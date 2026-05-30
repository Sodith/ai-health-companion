"""JWT authentication middleware.

This middleware runs on every request BEFORE the route handler.
For protected paths (anything not in the whitelist), it:
  1. Extracts the Bearer token from the Authorization header.
  2. Decodes and validates it.
  3. Attaches user claims to request.state so downstream code can use them.

Public paths (signup, login, docs, health) are skipped.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.utils.jwt import decode_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Paths that do NOT require authentication
PUBLIC_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Global JWT validation middleware."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip public endpoints
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Missing or invalid Authorization header.",
                    "data": None,
                    "error": "UNAUTHORIZED",
                },
            )

        token = auth_header.split(" ", 1)[1]

        try:
            payload = decode_access_token(token)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Token is invalid or has expired.",
                    "data": None,
                    "error": "UNAUTHORIZED",
                },
            )

        # Attach decoded claims to request state for downstream use
        request.state.user_id = payload.sub
        request.state.user_email = payload.email

        return await call_next(request)


