"""Auth controller — HTTP entry points for authentication.

Responsibilities (and ONLY these):
  1. Accept the HTTP request and validated payload.
  2. Call the correct service function.
  3. Wrap the result in an APIResponse and return it.

No business logic. No DB access. No try/except.
All errors bubble up to the global exception middleware automatically.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_model import User
from app.schemas.auth_schema import LoginData, LoginRequest, SignupData, SignupRequest
from app.schemas.common_schema import APIResponse
from app.schemas.user_schema import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------
@router.post(
    "/signup",
    response_model=APIResponse[SignupData],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    user, token = auth_service.signup(db, payload)
    return APIResponse.ok(
        data=SignupData(user=UserResponse.model_validate(user), access_token=token),
        message="Account created successfully.",
        status_code=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=APIResponse[LoginData],
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    _, token = auth_service.login(db, payload)
    return APIResponse.ok(
        data=LoginData(access_token=token),
        message="Login successful.",
        status_code=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get the currently authenticated user profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse.ok(
        data=UserResponse.model_validate(current_user),
        message="User profile fetched successfully.",
        status_code=status.HTTP_200_OK,
    )
