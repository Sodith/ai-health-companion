"""Prescription controller -- HTTP entry points for prescription management.
Responsibilities (and ONLY these):
  1. Accept the HTTP request and its parameters.
  2. Delegate to the prescription service.
  3. Wrap the result in an APIResponse envelope and return it.
No business logic. No DB access. No file I/O. No try/except.
All errors bubble up to the global exception middleware automatically.
Routes:
  POST   /prescriptions/upload     Upload a new prescription file.
  GET    /prescriptions            List all prescriptions for current user.
  GET    /prescriptions/{id}       Fetch a single prescription by ID.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_model import User
from app.schemas.common_schema import APIResponse
from app.schemas.prescription_schema import (
    PrescriptionDetail,
    PrescriptionListItem,
    PrescriptionUploadResponse,
)
from app.services import prescription_service
router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])
# ---------------------------------------------------------------------------
# POST /prescriptions/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=APIResponse[PrescriptionUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a prescription file",
    description=(
        "Upload a prescription as PDF, JPG, JPEG, or PNG (max 10 MB). "
        "Optionally include free-text symptom notes. "
        "Requires a valid Bearer JWT."
    ),
)
async def upload_prescription(
    prescription_file: UploadFile = File(
        ...,
        description="Prescription file -- PDF, JPG, JPEG, or PNG. Max 10 MB.",
    ),
    symptoms: str | None = Form(
        default=None,
        description="Free-text description of symptoms or health concerns (optional).",
        max_length=2000,
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PrescriptionUploadResponse]:
    data = await prescription_service.upload_prescription(
        db=db,
        user_id=current_user.id,
        file=prescription_file,
        symptoms=symptoms,
    )
    return APIResponse.ok(
        data=data,
        message="Prescription uploaded successfully.",
        status_code=status.HTTP_201_CREATED,
    )
# ---------------------------------------------------------------------------
# GET /prescriptions
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=APIResponse[list[PrescriptionListItem]],
    status_code=status.HTTP_200_OK,
    summary="List all prescriptions for the authenticated user",
    description=(
        "Returns all prescriptions belonging to the current user, "
        "sorted by upload date (newest first). "
        "Requires a valid Bearer JWT."
    ),
)
def list_prescriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[PrescriptionListItem]]:
    data = prescription_service.get_user_prescriptions(
        db=db,
        user_id=current_user.id,
    )
    return APIResponse.ok(
        data=data,
        message="Prescriptions fetched successfully.",
        status_code=status.HTTP_200_OK,
    )
# ---------------------------------------------------------------------------
# GET /prescriptions/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{prescription_id}",
    response_model=APIResponse[PrescriptionDetail],
    status_code=status.HTTP_200_OK,
    summary="Get a single prescription by ID",
    description=(
        "Fetches the full detail of a single prescription. "
        "Returns 404 if the record does not exist or belongs to another user. "
        "Requires a valid Bearer JWT."
    ),
)
def get_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PrescriptionDetail]:
    data = prescription_service.get_prescription_by_id(
        db=db,
        user_id=current_user.id,
        prescription_id=prescription_id,
    )
    return APIResponse.ok(
        data=data,
        message="Prescription fetched successfully.",
        status_code=status.HTTP_200_OK,
    )
