"""User-facing Pydantic schemas.

These schemas represent how user data is serialised and returned
in API responses. They are deliberately decoupled from the ORM model
so DB internals (password_hash, server-side fields) are never leaked.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public representation of a user account returned in responses.

    Never includes password_hash or any credential material.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    is_active: bool
    created_at: datetime
