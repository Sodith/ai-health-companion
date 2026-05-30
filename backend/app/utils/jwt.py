"""JWT access token creation and decoding.

We use python-jose which wraps OpenSSL under the hood.

Token structure (claims):
  sub   — user UUID (subject)
  email — user email (handy for quick lookups without a DB hit)
  exp   — expiry timestamp (UTC Unix epoch, set automatically)
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.schemas.auth_schema import TokenPayload
from app.utils.config import get_settings

settings = get_settings()


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT that expires after the configured number of minutes."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT.

    Raises:
        ValueError: if the token is expired, tampered with, or malformed.
    """
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**raw)
    except JWTError as exc:
        # Mask internal details — caller decides what HTTP status to send.
        raise ValueError("Invalid or expired token.") from exc
