"""Prescription request / response Pydantic schemas.

Covers:
  - PrescriptionUploadResponse   Data envelope returned after a successful upload.
  - PrescriptionListItem         Lightweight row used in GET /prescriptions list.
  - PrescriptionDetail           Full record used in GET /prescriptions/{id}.

Design rules:
  - Never expose stored_file_name or file_path in list responses (security).
  - Full detail (stored_file_name, file_path) is only returned on single-record
    fetch so internal storage paths are not broadcast in bulk payloads.
  - All schemas use ConfigDict(from_attributes=True) so they can be initialised
    directly from SQLAlchemy ORM instances.
  - Align with the existing APIResponse[T] envelope in common_schema.py.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# POST /prescriptions/upload  ── response data envelope
# ---------------------------------------------------------------------------

class PrescriptionUploadResponse(BaseModel):
    """Data field returned inside APIResponse after a successful file upload.

    Matches the contract agreed in Step 3:
        {
            "upload_id": 123,
            "filename": "<uuid>.<ext>",
            "status": "uploaded"
        }
    """

    model_config = ConfigDict(from_attributes=True)

    upload_id: int = Field(..., description="Auto-generated primary key of the new record.")
    filename: str = Field(..., description="UUID-based stored filename written to disk.")
    status: str = Field(..., description="Lifecycle status: uploaded | processing | processed | failed.")


# ---------------------------------------------------------------------------
# GET /prescriptions  ── list item (lightweight, no storage paths)
# ---------------------------------------------------------------------------

class PrescriptionListItem(BaseModel):
    """A single row in the GET /prescriptions list response.

    Intentionally omits stored_file_name and file_path to avoid leaking
    internal storage details in bulk responses.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    original_file_name: str = Field(..., description="Original client-supplied filename (display only).")
    file_type: str = Field(..., description="Canonical lowercase extension: pdf | jpg | jpeg | png.")
    file_size: int = Field(..., description="File size in bytes.")
    symptoms: str | None = Field(None, description="Free-text health notes supplied by the user.")
    upload_status: str = Field(..., description="Current lifecycle status of the upload.")
    analysis_status: str | None = Field(None, description="AI analysis status: pending | processing | completed | failed | None if not yet triggered.")
    created_at: datetime


# ---------------------------------------------------------------------------
# GET /prescriptions/{id}  ── full detail record
# ---------------------------------------------------------------------------

class PrescriptionDetail(BaseModel):
    """Full prescription record returned for a single-fetch request.

    Includes storage metadata (stored_file_name, file_path) which is safe
    to expose on a per-record, ownership-verified endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str = Field(..., description="UUID of the owning user.")
    original_file_name: str
    stored_file_name: str = Field(..., description="UUID-based filename written to disk.")
    file_path: str = Field(..., description="Relative path from project root to the stored file.")
    file_type: str
    file_size: int
    symptoms: str | None
    upload_status: str
    created_at: datetime
    updated_at: datetime

