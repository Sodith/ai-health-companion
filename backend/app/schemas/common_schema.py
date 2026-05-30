"""Common API response envelope schema.

Every API response is wrapped in this structure so the client always
receives a consistent payload shape regardless of the endpoint.

Shape:
    {
        "success": bool,
        "status_code": int,
        "message": str,
        "data": <T> | null,
        "error": str | null
    }
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope returned by every API endpoint."""

    success: bool
    status_code: int
    message: str
    data: T | None = None
    error: Any | None = None

    @classmethod
    def ok(
        cls,
        data: T | None = None,
        message: str = "Success",
        status_code: int = 200,
    ) -> "APIResponse[T]":
        """Convenience factory for successful responses."""
        return cls(
            success=True,
            status_code=status_code,
            message=message,
            data=data,
            error=None,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        status_code: int = 400,
        error: Any | None = None,
    ) -> "APIResponse[None]":
        """Convenience factory for error responses."""
        return cls(
            success=False,
            status_code=status_code,
            message=message,
            data=None,
            error=error,
        )
