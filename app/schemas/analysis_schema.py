"""Analysis request / response Pydantic schemas.

Covers
------
GeminiMedicineItem      Internal model — validates a single medicine object
                        parsed from Gemini's raw JSON response.

GeminiAnalysisResult    Internal model — validates the full structured JSON
                        object returned by Gemini before any DB write occurs.
                        Never exposed directly to the HTTP layer.

MedicineResponse        HTTP response — serialises a Medicine ORM row for
                        inclusion in API responses.

AnalysisResponse        HTTP response — serialises a full AIAnalysis ORM row
                        (including nested medicines) for both POST and GET
                        endpoints.  Injects a hardcoded medical disclaimer.

Design Rules
------------
- ``GeminiAnalysisResult`` and ``GeminiMedicineItem`` are internal contracts
  only — they validate Gemini output and are never returned to clients.
- ``AnalysisResponse`` is the sole public shape used by both endpoints.
- ``doctor_advice`` and ``lifestyle_changes`` are stored in the DB as
  JSON-serialized TEXT strings.  The ``field_validator`` on ``AnalysisResponse``
  transparently deserializes them so clients always receive proper JSON arrays.
- ``ConfigDict(from_attributes=True)`` on all ORM-facing schemas allows direct
  construction from SQLAlchemy model instances.
- The ``disclaimer`` field is injected at the schema layer — never stored in DB.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# DISCLAIMER — injected into every analysis response automatically
# ---------------------------------------------------------------------------

_DISCLAIMER = (
    "This analysis is AI-generated and is NOT a substitute for professional "
    "medical advice. Always consult a qualified healthcare provider."
)


# ===========================================================================
# INTERNAL schemas — Gemini JSON validation (never returned to HTTP clients)
# ===========================================================================

class GeminiMedicineItem(BaseModel):
    """Validates a single medicine object extracted from Gemini's JSON output."""

    medicine_name: str = Field(..., min_length=1, description="Name of the medicine.")
    dosage: str | None = Field(None, description="Dosage, e.g. '500mg'.")
    frequency: str | None = Field(None, description="Frequency, e.g. '2 times daily'.")
    duration: str | None = Field(None, description="Duration, e.g. '30 days'.")
    notes: str | None = Field(None, description="Extra per-medicine context.")


class GeminiAnalysisResult(BaseModel):
    """Validates the full structured JSON object returned by Gemini.

    Used exclusively in GeminiService → AnalysisService handoff.
    All fields except ``medicines`` are nullable — Gemini may not always
    extract every piece of information from a low-quality scan.
    """

    disease_detected: str | None = Field(
        None,
        description="Disease(s) identified from the prescription.",
    )
    doctor_advice: list[str] = Field(
        default_factory=list,
        description="List of doctor advice strings.",
    )
    lifestyle_changes: list[str] = Field(
        default_factory=list,
        description="List of lifestyle recommendation strings.",
    )
    medicines: list[GeminiMedicineItem] = Field(
        default_factory=list,
        description="List of medicines extracted from the prescription.",
    )


# ===========================================================================
# PUBLIC schemas — HTTP response contracts
# ===========================================================================

class MedicineResponse(BaseModel):
    """Serialises a single Medicine ORM row for inclusion in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Medicine primary key.")
    medicine_name: str = Field(..., description="Name of the medicine.")
    dosage: str | None = Field(None, description="Dosage, e.g. '500mg'.")
    frequency: str | None = Field(None, description="Frequency, e.g. '2 times daily'.")
    duration: str | None = Field(None, description="Duration, e.g. '30 days'.")
    notes: str | None = Field(None, description="Extra per-medicine context.")
    created_at: datetime
    updated_at: datetime


class AnalysisResponse(BaseModel):
    """Serialises a full AIAnalysis ORM row for both POST and GET endpoints.

    Transparently deserialises ``doctor_advice`` and ``lifestyle_changes``
    from their DB-stored JSON TEXT representation back into proper Python
    lists before serialisation to the HTTP client.

    The ``disclaimer`` field is hardcoded here — it is never stored in the DB.
    """


    analysis_id: int = Field(..., alias="id", description="Analysis primary key.")
    prescription_id: int = Field(..., description="FK to the analyzed prescription.")
    analysis_status: str = Field(..., description="pending | processing | completed | failed.")

    disease_detected: str | None = Field(
        None,
        description="Disease(s) identified by Gemini.",
    )
    doctor_advice: list[str] = Field(
        default_factory=list,
        description="List of doctor advice strings.",
    )
    lifestyle_changes: list[str] = Field(
        default_factory=list,
        description="List of lifestyle recommendation strings.",
    )
    medicines: list[MedicineResponse] = Field(
        default_factory=list,
        description="Medicines extracted from the prescription.",
    )

    disclaimer: str = Field(
        default=_DISCLAIMER,
        description="Mandatory medical disclaimer — AI output is not a substitute for professional advice.",
    )

    created_at: datetime
    updated_at: datetime

    # ------------------------------------------------------------------
    # Validators — transparently deserialize JSON-text list fields
    # ------------------------------------------------------------------

    @field_validator("doctor_advice", mode="before")
    @classmethod
    def parse_doctor_advice(cls, v: Any) -> list[str]:
        """Deserialize doctor_advice from a JSON string if stored as TEXT in DB."""
        return _parse_json_list(v, field_name="doctor_advice")

    @field_validator("lifestyle_changes", mode="before")
    @classmethod
    def parse_lifestyle_changes(cls, v: Any) -> list[str]:
        """Deserialize lifestyle_changes from a JSON string if stored as TEXT in DB."""
        return _parse_json_list(v, field_name="lifestyle_changes")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,   # allows both 'id' and 'analysis_id' alias
    )


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------

def _parse_json_list(value: Any, field_name: str) -> list[str]:
    """Parse a value that may be a JSON string, a list, or None into list[str].

    DB stores these fields as serialized JSON TEXT (e.g. '["advice 1"]').
    When the ORM model is constructed directly in tests or service layer
    with a real list, this validator passes it through unchanged.

    Args:
        value:      Raw value from ORM attribute or constructor.
        field_name: Field name — used only in error messages.

    Returns:
        A list of strings.  Empty list if value is None or empty string.
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            # Gemini occasionally returns a plain string instead of a list
            return [str(parsed)]
        except json.JSONDecodeError:
            # Treat a raw non-JSON string as a single-item list
            return [value]
    return []

