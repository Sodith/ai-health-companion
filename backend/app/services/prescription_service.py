"""Prescription business logic.

This layer sits between the controller (HTTP) and the database (ORM).
It orchestrates the full upload lifecycle and all read operations.

Responsibilities:
  - Delegate file validation and storage to file_utility.
  - Persist prescription metadata to the DB.
  - Roll back (delete saved file) if the DB insert fails.
  - Query prescriptions with strict user-ownership enforcement.

The controller only calls these functions — it never touches the DB or
file system directly.  All errors are raised as AppException subclasses
so the global exception middleware formats them automatically.
"""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.analysis_model import AIAnalysis
from app.models.prescription_model import Prescription
from app.schemas.prescription_schema import (
    PrescriptionDetail,
    PrescriptionListItem,
    PrescriptionUploadResponse,
)
from app.utils.exceptions import BadRequestException, NotFoundException
from app.utils.file_utility import delete_file, validate_and_save
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def upload_prescription(
    db: Session,
    user_id: str,
    file: UploadFile,
    symptoms: str | None,
) -> PrescriptionUploadResponse:
    """Validate, store, and persist a prescription file upload.

    Flow:
      1. File utility validates extension, MIME, size, and writes to disk.
      2. A Prescription row is inserted into the DB.
      3. If the DB insert fails, the saved file is removed (orphan cleanup).

    Args:
        db:       Active SQLAlchemy session.
        user_id:  UUID of the authenticated user (from JWT).
        file:     UploadFile from the multipart request.
        symptoms: Optional free-text health notes.

    Returns:
        PrescriptionUploadResponse with upload_id, filename, and status.

    Raises:
        BadRequestException: on validation or storage failure.
        AppException:        on unexpected DB failure.
    """
    if not file:
        raise BadRequestException("Prescription file is required.")

    # 1. Validate and save to disk
    metadata = await validate_and_save(file)

    # 2. Persist to DB — clean up file if this fails
    try:
        prescription = Prescription(
            user_id=user_id,
            original_file_name=metadata.original_file_name,
            stored_file_name=metadata.stored_file_name,
            file_path=metadata.file_path,
            file_type=metadata.file_type,
            file_size=metadata.file_size,
            symptoms=symptoms.strip() if symptoms else None,
            upload_status="uploaded",
        )
        db.add(prescription)
        db.commit()
        db.refresh(prescription)

    except Exception as exc:
        db.rollback()
        # Best-effort cleanup — remove the saved file to avoid orphans
        delete_file(metadata.file_path)
        logger.error(
            "DB insert failed for user '%s', file '%s': %s",
            user_id,
            metadata.stored_file_name,
            exc,
        )
        raise BadRequestException("File upload failed. Please try again.") from exc

    logger.info(
        "Prescription uploaded: id=%s user=%s file='%s'",
        prescription.id,
        user_id,
        metadata.stored_file_name,
    )

    return PrescriptionUploadResponse(
        upload_id=prescription.id,
        filename=prescription.stored_file_name,
        status=prescription.upload_status,
    )


# ---------------------------------------------------------------------------
# List — all prescriptions for the authenticated user
# ---------------------------------------------------------------------------

def get_user_prescriptions(
    db: Session,
    user_id: str,
) -> list[PrescriptionListItem]:
    """Return all prescriptions belonging to *user_id*, newest first.

    Args:
        db:      Active SQLAlchemy session.
        user_id: UUID of the authenticated user.

    Returns:
        List of PrescriptionListItem (lightweight, no storage paths).
    """
    rows = (
        db.query(Prescription)
        .filter(Prescription.user_id == user_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    items = []
    for row in rows:
        # Look up analysis status for this prescription (None if never triggered)
        analysis = (
            db.query(AIAnalysis)
            .filter(AIAnalysis.prescription_id == row.id)
            .first()
        )
        item = PrescriptionListItem.model_validate(row)
        item.analysis_status = analysis.analysis_status if analysis else None
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Detail — single prescription with ownership check
# ---------------------------------------------------------------------------

def get_prescription_by_id(
    db: Session,
    user_id: str,
    prescription_id: int,
) -> PrescriptionDetail:
    """Return a single prescription record, enforcing user ownership.

    Args:
        db:               Active SQLAlchemy session.
        user_id:          UUID of the authenticated user.
        prescription_id:  Primary key of the prescription.

    Returns:
        PrescriptionDetail (full record including storage paths).

    Raises:
        NotFoundException: if the record does not exist or belongs to another user.
    """
    row = (
        db.query(Prescription)
        .filter(
            Prescription.id == prescription_id,
            Prescription.user_id == user_id,
        )
        .first()
    )

    if not row:
        raise NotFoundException("Prescription not found.")

    return PrescriptionDetail.model_validate(row)

