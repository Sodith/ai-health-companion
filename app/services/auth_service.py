"""Authentication business logic.

This layer sits between the controller (HTTP) and the database (ORM).
It owns all auth rules: duplicate email check, credential validation,
token generation, and fetching the current user.

The controller only calls these functions — it never touches the DB directly.
All errors are raised as AppException so the global exception middleware
formats them into a consistent APIResponse automatically.
"""

from sqlalchemy.orm import Session

from app.models.user_model import User
from app.schemas.auth_schema import LoginRequest, SignupRequest
from app.utils.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.utils.jwt import create_access_token
from app.utils.logger import get_logger
from app.utils.password import hash_password, verify_password

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the user row matching the given email, or None."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Return the user row matching the given UUID, or None."""
    return db.query(User).filter(User.id == user_id).first()


# ---------------------------------------------------------------------------
# Auth operations
# ---------------------------------------------------------------------------

def signup(db: Session, payload: SignupRequest) -> tuple[User, str]:
    """Register a new user account.

    Returns:
        (user, access_token) on success.

    Raises:
        ConflictException: if the email is already registered.
    """
    if get_user_by_email(db, payload.email):
        raise ConflictException(f"Email '{payload.email}' is already registered.")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)

    logger.info("New user registered: %s (id=%s)", user.email, user.id)
    return user, token


def login(db: Session, payload: LoginRequest) -> tuple[User, str]:
    """Authenticate a user with email + password.

    Returns:
        (user, access_token) on success.

    Raises:
        UnauthorizedException: if credentials are invalid.
    """
    user = get_user_by_email(db, payload.email)

    # Always call verify_password even if user is None to prevent
    # timing attacks that could reveal whether an email exists.
    password_ok = verify_password(payload.password, user.password_hash) if user else False

    if not user or not password_ok:
        raise UnauthorizedException("Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated. Please contact support.")

    token = create_access_token(user_id=user.id, email=user.email)

    logger.info("User logged in: %s (id=%s)", user.email, user.id)
    return user, token


def get_current_user_from_token(db: Session, user_id: str) -> User:
    """Fetch the active user for the decoded JWT subject claim.

    Raises:
        UnauthorizedException: if the user no longer exists or is inactive.
    """
    user = get_user_by_id(db, user_id)

    if not user:
        raise NotFoundException("User account not found.")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated.")

    return user
