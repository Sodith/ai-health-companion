"""FastAPI dependency for resolving the authenticated user on protected routes.

Usage in any route:
    from app.dependencies.auth_dependency import get_current_user

    @router.get("/me")
    def me(current_user: User = Depends(get_current_user)):
        ...

Flow:
    1. FastAPI extracts the Bearer token from the Authorization header.
    2. We decode the JWT and pull out the user_id (sub claim).
    3. We hit the DB to confirm the user still exists and is active.
    4. The resolved User object is injected into the route handler.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user_model import User
from app.services import auth_service
from app.utils.exceptions import UnauthorizedException
from app.utils.jwt import decode_access_token

# auto_error=False so we return a clean APIResponse instead of FastAPI's default 403
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and return the matching active User.

    Raises UnauthorizedException (→ 401) if the token is missing,
    invalid, expired, or the user no longer exists / is inactive.
    """
    if not credentials:
        raise UnauthorizedException("Authorization header is missing.")

    try:
        token_data = decode_access_token(credentials.credentials)
    except ValueError:
        raise UnauthorizedException("Token is invalid or has expired.")

    # get_current_user_from_token raises UnauthorizedException / NotFoundException
    return auth_service.get_current_user_from_token(db, token_data.sub)
