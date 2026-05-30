"""Analysis controller — HTTP entry points for AI prescription analysis.

Responsibilities (and ONLY these)
----------------------------------
1. Accept the HTTP request and path parameters.
2. Delegate entirely to ``analysis_service``.
3. Wrap the result in the standard ``APIResponse`` envelope.
4. Return the correct HTTP status code.

No business logic. No DB queries. No Gemini calls. No try/except.
All errors bubble up to the global exception middleware automatically.

Routes
------
  POST   /analysis/{prescription_id}   Trigger AI analysis (idempotent).
  GET    /analysis/{prescription_id}   Retrieve stored analysis result.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_model import User
from app.schemas.analysis_schema import AnalysisResponse
from app.schemas.common_schema import APIResponse
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ---------------------------------------------------------------------------
# POST /analysis/{prescription_id}
# ---------------------------------------------------------------------------

@router.post(
    "/{prescription_id}",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI analysis for a prescription",
    description=(
        "Analyzes the uploaded prescription using Gemini AI and returns structured results "
        "including detected diseases, prescribed medicines with dosage schedules, "
        "doctor advice, and lifestyle recommendations.\n\n"
        "**Idempotent:** If a completed analysis already exists for this prescription, "
        "the cached result is returned immediately — Gemini is **never** called again.\n\n"
        "**Ownership enforced:** The prescription must belong to the authenticated user.\n\n"
        "Requires a valid Bearer JWT."
    ),
)
def trigger_analysis(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[AnalysisResponse]:
    """Trigger or return cached AI analysis for a prescription.

    - If analysis is ``completed``  → returns cached result with HTTP 200.
    - If analysis is ``processing`` → returns HTTP 409 (Conflict).
    - If analysis is ``failed``     → retries and returns HTTP 201.
    - If no analysis exists         → runs Gemini and returns HTTP 201.
    """
    data, http_status = analysis_service.trigger_analysis(
        db=db,
        user_id=current_user.id,
        prescription_id=prescription_id,
    )

    if http_status == status.HTTP_200_OK:
        envelope = APIResponse.ok(
            data=data,
            message="Analysis already completed. Returning cached result.",
            status_code=status.HTTP_200_OK,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=envelope.model_dump(mode="json"),
        )

    return APIResponse.ok(
        data=data,
        message="Prescription analyzed successfully.",
        status_code=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# GET /analysis/{prescription_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{prescription_id}",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored AI analysis for a prescription",
    description=(
        "Returns the stored AI analysis result for the given prescription.\n\n"
        "**Never calls Gemini.** Returns whatever is currently persisted — "
        "including ``pending``, ``processing``, ``completed``, or ``failed`` states.\n\n"
        "**Ownership enforced:** The prescription must belong to the authenticated user.\n\n"
        "Requires a valid Bearer JWT."
    ),
)
def get_analysis(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[AnalysisResponse]:
    """Return the stored analysis result for a prescription.

    Does NOT trigger a new Gemini analysis.
    Use POST /analysis/{prescription_id} to generate or retry an analysis.
    """
    data = analysis_service.get_analysis(
        db=db,
        user_id=current_user.id,
        prescription_id=prescription_id,
    )

    return APIResponse.ok(
        data=data,
        message="Analysis retrieved successfully.",
        status_code=status.HTTP_200_OK,
    )

