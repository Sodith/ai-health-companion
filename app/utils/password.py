"""Password hashing and verification using bcrypt directly.

We use the `bcrypt` package directly instead of passlib because passlib 1.7.x
is abandoned and broken against bcrypt >= 4.0 on Python 3.12+.

bcrypt handles salt generation automatically on every hash call.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password and return a bcrypt digest string."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
