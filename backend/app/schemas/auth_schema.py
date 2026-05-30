"""Auth request/response Pydantic schemas.

Covers:
  - SignupRequest   — body for POST /auth/signup
  - LoginRequest    — body for POST /auth/login
  - TokenResponse   — JWT token payload returned after sign-up / login
  - SignupData      — data envelope for sign-up response (user + token)
  - LoginData       — data envelope for login response (token only)
  - TokenPayload    — internal model for decoded JWT claims (not HTTP)
"""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user_schema import UserResponse


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    """Payload accepted by POST /auth/signup."""

    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["StrongPass@123"],
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """Enforce password complexity: upper, lower, digit, special char."""
        errors: list[str] = []
        if not re.search(r"[A-Z]", value):
            errors.append("at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            errors.append("at least one lowercase letter")
        if not re.search(r"\d", value):
            errors.append("at least one digit")
        if not re.search(r"[^A-Za-z0-9]", value):
            errors.append("at least one special character")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return value


class LoginRequest(BaseModel):
    """Payload accepted by POST /auth/login."""

    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=1, max_length=64)


# ---------------------------------------------------------------------------
# Response data schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """JWT token block included in auth responses."""

    access_token: str
    token_type: str = "bearer"


class SignupData(BaseModel):
    """Data field inside the sign-up APIResponse envelope."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class LoginData(BaseModel):
    """Data field inside the login APIResponse envelope."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Internal token claim schema (used by JWT utility, not exposed via HTTP)
# ---------------------------------------------------------------------------

class TokenPayload(BaseModel):
    """Claims decoded from a JWT access token."""

    sub: str          # user UUID
    email: str
    exp: int          # Unix timestamp — validated by python-jose automatically
