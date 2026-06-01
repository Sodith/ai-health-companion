"""Analysis business logic.

Orchestrates the full AI analysis lifecycle for a prescription.
This layer sits between the controller (HTTP) and the database (ORM),
and coordinates with GeminiService for all AI operations.

Responsibilities
----------------
- Verify prescription exists and belongs to the requesting user.
- Enforce idempotency: never call Gemini twice for a completed analysis.
- Manage the AIAnalysis status lifecycle: pending → processing → completed | failed.
- Persist AIAnalysis and Medicine rows atomically.
- Serialize JSON list fields (doctor_advice, lifestyle_changes) for DB storage.
- Deserialize ORM rows into typed AnalysisResponse objects for the controller.

The controller only calls the two public functions here.
All errors are raised as AppException subclasses so the global exception
middleware formats them into the standard APIResponse envelope automatically.

Status Machine
--------------
    POST /analysis/{id}:
        "completed"  → return cached result immediately (no Gemini call)
        "processing" → raise ConflictException(409)
        "failed"     → delete stale medicines, reset row, retry Gemini
        (none)       → create new row, call Gemini

    GET /analysis/{id}:
        any status   → return stored row as-is
        (none)       → raise NotFoundException(404)
"""

from __future__ import annotations

import json

from fastapi import status
from sqlalchemy.orm import Session

from app.models.analysis_model import AIAnalysis
from app.models.medicine_model import Medicine
from app.models.prescription_model import Prescription
from app.schemas.analysis_schema import AnalysisResponse
from app.services import gemini_service
from app.utils.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_owned_prescription(
    db: Session,
    user_id: str,
    prescription_id: int,
) -> Prescription:
    """Fetch a prescription row and enforce user ownership.

    Args:
        db:               Active SQLAlchemy session.
        user_id:          UUID of the authenticated user.
        prescription_id:  PK of the prescription to load.

    Returns:
        The ``Prescription`` ORM row.

    Raises:
        NotFoundException:  if no prescription exists with that ID.
        ForbiddenException: if the prescription belongs to a different user.
    """
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .first()
    )

    if not prescription:
        raise NotFoundException(f"Prescription {prescription_id} not found.")

    if prescription.user_id != user_id:
        raise ForbiddenException(
            "You do not have permission to analyze this prescription."
        )

    return prescription


def _get_existing_analysis(
    db: Session,
    prescription_id: int,
) -> AIAnalysis | None:
    """Return an existing AIAnalysis row for the given prescription, or None.

    Args:
        db:               Active SQLAlchemy session.
        prescription_id:  PK of the prescription.

    Returns:
        ``AIAnalysis`` ORM row, or ``None`` if no analysis exists yet.
    """
    return (
        db.query(AIAnalysis)
        .filter(AIAnalysis.prescription_id == prescription_id)
        .first()
    )


def _serialize_list(values: list[str]) -> str:
    """Serialize a Python list to a JSON string for DB TEXT storage.

    Args:
        values: List of strings (doctor_advice or lifestyle_changes).

    Returns:
        JSON-encoded string, e.g. '["Take after meals", "Drink water"]'.
    """
    return json.dumps(values)


def _persist_analysis(
    db: Session,
    analysis: AIAnalysis,
    gemini_result,
) -> None:
    """Write Gemini results into the AIAnalysis row and insert Medicine rows.

    Mutates ``analysis`` in place, then bulk-inserts all Medicine rows.
    Called inside a try/except block in the public service function.

    Args:
        db:            Active SQLAlchemy session (not yet committed).
        analysis:      AIAnalysis ORM row to update (already in session).
        gemini_result: Validated ``GeminiAnalysisResult`` from GeminiService.
    """
    # Update analysis fields
    analysis.disease_detected  = gemini_result.disease_detected
    analysis.doctor_advice     = _serialize_list(gemini_result.doctor_advice)
    analysis.lifestyle_changes = _serialize_list(gemini_result.lifestyle_changes)
    analysis.raw_response      = json.dumps(gemini_result.model_dump())
    analysis.analysis_status   = "completed"

    # Insert Medicine rows
    for med in gemini_result.medicines:
        medicine = Medicine(
            analysis_id   = analysis.id,
            medicine_name = med.medicine_name,
            dosage        = med.dosage,
            frequency     = med.frequency,
            duration      = med.duration,
            notes         = med.notes,
        )
        db.add(medicine)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def trigger_analysis(
    db: Session,
    user_id: str,
    prescription_id: int,
) -> tuple[AnalysisResponse, int]:
    """Trigger (or return cached) AI analysis for a prescription.

    Idempotency contract:
        - ``completed``  → return cached result, HTTP 200.
        - ``processing`` → raise ConflictException, HTTP 409.
        - ``failed``     → reset and retry, HTTP 201 on success.
        - (none)         → create new row and call Gemini, HTTP 201 on success.

    Args:
        db:               Active SQLAlchemy session.
        user_id:          UUID of the authenticated user (from JWT).
        prescription_id:  PK of the prescription to analyze.

    Returns:
        Tuple of (AnalysisResponse, http_status_code).

    Raises:
        NotFoundException:   if the prescription does not exist.
        ForbiddenException:  if the prescription belongs to another user.
        ConflictException:   if analysis is currently processing.
        BadRequestException: if the prescription file is missing from disk.
        AppException:        on Gemini API failures or DB errors.
    """
    # 1. Verify prescription ownership
    prescription = _get_owned_prescription(db, user_id, prescription_id)

    # 2. Check for existing analysis — enforce idempotency
    existing = _get_existing_analysis(db, prescription_id)

    if existing:
        if existing.analysis_status == "completed":
            logger.info(
                "Analysis cache hit | prescription_id=%s analysis_id=%s",
                prescription_id,
                existing.id,
            )
            # Eagerly load medicines for serialization
            db.refresh(existing)
            return (
                AnalysisResponse.model_validate(existing),
                status.HTTP_200_OK,
            )

        if existing.analysis_status == "processing":
            raise ConflictException(
                "Analysis is currently in progress. Please wait and try again."
            )

        # status == "failed" — reset for retry
        logger.info(
            "Retrying failed analysis | prescription_id=%s analysis_id=%s",
            prescription_id,
            existing.id,
        )
        # Remove stale medicine rows from previous failed attempt
        db.query(Medicine).filter(Medicine.analysis_id == existing.id).delete()
        analysis = existing
        analysis.analysis_status  = "processing"
        analysis.disease_detected = None
        analysis.doctor_advice    = None
        analysis.lifestyle_changes = None
        analysis.raw_response     = None
        db.flush()

    else:
        # 3. Create new analysis row in "processing" state
        analysis = AIAnalysis(
            prescription_id  = prescription_id,
            analysis_status  = "processing",
        )
        db.add(analysis)
        db.flush()  # Assigns analysis.id without committing
        logger.info(
            "New analysis started | prescription_id=%s analysis_id=%s",
            prescription_id,
            analysis.id,
        )

    # 4. Call Gemini — if this raises, we catch below and mark as failed
    try:
        gemini_result = gemini_service.analyze_prescription(
            file_path = prescription.file_path,
            file_type = prescription.file_type,
            symptoms  = prescription.symptoms,
        )

    except Exception as exc:
        # Mark the analysis row as failed before re-raising
        try:
            analysis.analysis_status = "failed"
            db.commit()
        except Exception as db_exc:
            logger.error(
                "Failed to persist 'failed' status for analysis_id=%s: %s",
                analysis.id,
                db_exc,
            )
            db.rollback()

        logger.error(
            "Gemini call failed for prescription_id=%s: %s",
            prescription_id,
            exc,
        )
        raise  # Re-raise the original AppException from GeminiService

    # 5. Persist results atomically
    try:
        _persist_analysis(db, analysis, gemini_result)
        db.commit()
        db.refresh(analysis)

    except Exception as exc:
        db.rollback()
        # Best-effort: mark as failed so the user can retry
        try:
            analysis.analysis_status = "failed"
            db.commit()
        except Exception:
            db.rollback()

        logger.error(
            "DB persist failed for analysis_id=%s: %s",
            analysis.id,
            exc,
        )
        raise AppException(
            message="Failed to save analysis results. Please try again.",
            status_code=500,
        ) from exc

    logger.info(
        "Analysis persisted | prescription_id=%s analysis_id=%s medicines=%d",
        prescription_id,
        analysis.id,
        len(analysis.medicines),
    )

    # 6. Auto-create medicine schedules for reminder system (Phase 7)
    try:
        from app.services.reminder_service import create_schedules_from_analysis
        create_schedules_from_analysis(db, str(user_id), analysis.id)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to create medicine schedules: %s", exc)
        # Non-critical — don't fail the analysis response

    return (
        AnalysisResponse.model_validate(analysis),
        status.HTTP_201_CREATED,
    )


def get_analysis(
    db: Session,
    user_id: str,
    prescription_id: int,
) -> AnalysisResponse:
    """Retrieve the stored analysis for a prescription.

    Never calls Gemini.  Returns whatever is stored — including
    ``pending``, ``processing``, or ``failed`` states.

    Args:
        db:               Active SQLAlchemy session.
        user_id:          UUID of the authenticated user (from JWT).
        prescription_id:  PK of the prescription whose analysis to retrieve.

    Returns:
        ``AnalysisResponse`` serialized from the stored AIAnalysis row.

    Raises:
        NotFoundException:  if the prescription does not exist.
        ForbiddenException: if the prescription belongs to another user.
        NotFoundException:  if no analysis record exists for the prescription.
    """
    # 1. Verify prescription ownership (raises 404 / 403 automatically)
    _get_owned_prescription(db, user_id, prescription_id)

    # 2. Load the analysis row
    analysis = _get_existing_analysis(db, prescription_id)

    if not analysis:
        raise NotFoundException(
            f"No analysis found for prescription {prescription_id}. "
            "Submit a POST request to /analysis/{prescription_id} to generate one."
        )

    logger.info(
        "Analysis retrieved | prescription_id=%s analysis_id=%s status=%s",
        prescription_id,
        analysis.id,
        analysis.analysis_status,
    )

    return AnalysisResponse.model_validate(analysis)

