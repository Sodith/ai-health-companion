"""File utility for secure prescription upload handling.

Responsibilities:
  - Validate file size (≤ 10 MB).
  - Validate file extension against the allowlist.
  - Validate MIME type against the allowlist.
  - Cross-check that extension and MIME type agree.
  - Generate a UUID-based stored filename (never trust client name).
  - Build a date-partitioned storage path: uploads/prescriptions/YYYY/MM/DD/
  - Prevent path traversal by verifying the resolved path stays under the
    upload root.
  - Save the file to disk and return normalised metadata.
  - Provide a cleanup helper so the service can remove orphan files on
    DB-insert failure.

Nothing in here touches the database.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import UploadFile

from app.utils.exceptions import BadRequestException
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "jpg", "jpeg", "png"})

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {"application/pdf", "image/jpeg", "image/png"}
)

# Maps extension → expected MIME types (one extension may map to >1 MIME)
EXTENSION_MIME_MAP: dict[str, frozenset[str]] = {
    "pdf":  frozenset({"application/pdf"}),
    "jpg":  frozenset({"image/jpeg"}),
    "jpeg": frozenset({"image/jpeg"}),
    "png":  frozenset({"image/png"}),
}

# Base upload directory (relative to project root)
UPLOAD_BASE_DIR: str = "uploads/prescriptions"


# ---------------------------------------------------------------------------
# Return value dataclass
# ---------------------------------------------------------------------------

@dataclass
class SavedFileMetadata:
    """Metadata returned after a file is successfully written to disk."""

    original_file_name: str   # Client-supplied name (audit/display only)
    stored_file_name: str     # UUID-based filename on disk
    file_path: str            # Relative path from project root
    file_type: str            # Canonical lowercase extension
    file_size: int            # Bytes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_extension(filename: str) -> str:
    """Return the lowercased extension from a filename, without the dot.

    Raises:
        BadRequestException: if no extension is found.
    """
    _, dot_ext = os.path.splitext(filename)
    if not dot_ext:
        raise BadRequestException("Uploaded file has no extension.")
    return dot_ext.lstrip(".").lower()


def _build_date_dir() -> str:
    """Return a date-partitioned sub-directory path YYYY/MM/DD."""
    today = datetime.now(timezone.utc)
    return os.path.join(
        UPLOAD_BASE_DIR,
        str(today.year),
        f"{today.month:02d}",
        f"{today.day:02d}",
    )


def _safe_resolve(base: str, target: str) -> str:
    """Resolve *target* and assert it sits inside *base* (path traversal guard).

    Returns:
        The resolved absolute target path.

    Raises:
        BadRequestException: if the resolved path escapes the base directory.
    """
    abs_base = os.path.realpath(os.path.abspath(base))
    abs_target = os.path.realpath(os.path.abspath(target))
    if not abs_target.startswith(abs_base + os.sep) and abs_target != abs_base:
        raise BadRequestException("Invalid file path detected.")
    return abs_target


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_and_save(file: UploadFile) -> SavedFileMetadata:
    """Validate *file* and persist it to the date-partitioned upload directory.

    Validation order:
      1. Presence  — file and filename must exist.
      2. Extension — must be in ALLOWED_EXTENSIONS.
      3. MIME type — must be in ALLOWED_MIME_TYPES.
      4. Cross-check — extension and MIME type must agree.
      5. File size — content must be ≤ MAX_FILE_SIZE_BYTES.

    File is read fully into memory once for the size check, then written to
    disk.  This keeps the implementation simple while honouring the 10 MB cap.

    Returns:
        SavedFileMetadata with all fields needed for a DB insert.

    Raises:
        BadRequestException: on any validation failure.
        BadRequestException: if the file cannot be written to disk.
    """

    # 1. Presence
    if not file or not file.filename:
        raise BadRequestException("Prescription file is required.")

    original_name: str = file.filename

    # 2. Extension check
    ext = _extract_extension(original_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            f"Invalid file type '.{ext}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # 3. MIME type check
    content_type: str = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise BadRequestException(
            f"Invalid file content type '{content_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
        )

    # 4. Extension ↔ MIME cross-check
    if content_type not in EXTENSION_MIME_MAP.get(ext, frozenset()):
        raise BadRequestException(
            f"File extension '.{ext}' does not match content type '{content_type}'."
        )

    # 5. Read content + size check
    content: bytes = await file.read()
    file_size: int = len(content)
    if file_size == 0:
        raise BadRequestException("Uploaded file is empty.")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise BadRequestException(
            f"File size {file_size / (1024 * 1024):.2f} MB exceeds the 10 MB limit."
        )

    # Build storage path
    date_dir = _build_date_dir()
    stored_name = f"{uuid.uuid4()}.{ext}"
    relative_path = os.path.join(date_dir, stored_name).replace("\\", "/")

    # Path traversal guard
    _safe_resolve(UPLOAD_BASE_DIR, relative_path)

    # Create directory and write file
    try:
        os.makedirs(date_dir, exist_ok=True)
        with open(relative_path, "wb") as f:
            f.write(content)
    except OSError as exc:
        logger.error("Failed to write file '%s': %s", relative_path, exc)
        raise BadRequestException("File upload failed. Please try again.") from exc

    logger.info(
        "File saved: original='%s' stored='%s' size=%d bytes",
        original_name,
        stored_name,
        file_size,
    )

    return SavedFileMetadata(
        original_file_name=original_name,
        stored_file_name=stored_name,
        file_path=relative_path,
        file_type=ext,
        file_size=file_size,
    )


def delete_file(file_path: str) -> None:
    """Best-effort cleanup — remove a file from disk without raising.

    Called by the service layer when a DB insert fails after a successful
    file save, to prevent orphan files accumulating on disk.
    """
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info("Cleaned up orphan file: %s", file_path)
    except OSError as exc:
        # Log but never raise — cleanup failure must not shadow the original error.
        logger.warning("Could not delete orphan file '%s': %s", file_path, exc)

