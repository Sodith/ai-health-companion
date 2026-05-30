"""Gemini AI service.

Responsible for ALL communication with the Gemini API.
No other module in the application imports google.genai directly.

Responsibilities
----------------
1. Configure the Gemini client once at module load (not per request).
2. Read the prescription file from disk.
3. Construct a multimodal prompt (file bytes + symptom text).
4. Call ``gemini-2.5-flash`` with strict JSON-only output enforcement.
5. Strip any accidental markdown fences from the response (safety net).
6. Parse and validate the JSON response via Pydantic (GeminiAnalysisResult).
7. Return a typed ``GeminiAnalysisResult`` to the caller.

This service raises only ``AppException`` subclasses — all google.genai
exceptions are caught here and translated to HTTP-meaningful errors so the
rest of the codebase stays SDK-agnostic.

Integration
-----------
    Called exclusively by ``analysis_service.py``.
    Never called directly from a controller.
    Never stores anything to the database.
"""

from __future__ import annotations

import json
import os
import re

import google.genai as genai
import google.genai.types as genai_types
import google.api_core.exceptions as google_exceptions
from pydantic import ValidationError

from app.schemas.analysis_schema import GeminiAnalysisResult
from app.utils.config import get_settings
from app.utils.exceptions import AppException, BadRequestException
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# MIME type mapping — supported prescription file types
# ---------------------------------------------------------------------------
_MIME_TYPES: dict[str, str] = {
    "pdf":  "application/pdf",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
}

# ---------------------------------------------------------------------------
# Gemini model identifier
# ---------------------------------------------------------------------------
_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# System instruction — enforces strict JSON-only output from Gemini
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """You are a medical document analysis AI.
Your ONLY task is to analyze the uploaded prescription image or document and the patient's reported symptoms.
You MUST return a single valid JSON object and nothing else.
Rules:
- No markdown.
- No code fences (no ```json).
- No explanation text before or after the JSON.
- No preamble or commentary.
- Only output the raw JSON object.

Required JSON schema:
{
  "disease_detected": "string or null",
  "doctor_advice": ["string"],
  "lifestyle_changes": ["string"],
  "medicines": [
    {
      "medicine_name": "string",
      "dosage": "string or null",
      "frequency": "string or null",
      "duration": "string or null",
      "notes": "string or null"
    }
  ]
}

If a field cannot be determined from the prescription, use null for string fields or [] for array fields.
Never invent information that is not present in the prescription."""

# ---------------------------------------------------------------------------
# Generation config — near-deterministic, hard output cap
# ---------------------------------------------------------------------------
_GENERATION_CONFIG = genai_types.GenerateContentConfig(
    system_instruction=_SYSTEM_INSTRUCTION,
    temperature=0.1,
    top_p=0.95,
    max_output_tokens=8192,
    response_mime_type="application/json",
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
)

# ---------------------------------------------------------------------------
# Module-level Gemini client — initialized once on first use
# ---------------------------------------------------------------------------
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Return (or lazily initialize) the module-level Gemini client.

    The client is created once per process lifetime.  This avoids per-request
    authentication overhead while remaining testable via module-level patching.

    Returns:
        Configured ``genai.Client`` instance.

    Raises:
        AppException: if ``GEMINI_API_KEY`` is missing or empty.
    """
    global _client
    if _client is None:
        api_key = get_settings().gemini_api_key
        if not api_key:
            raise AppException(
                message="Gemini API key is not configured. Set GEMINI_API_KEY in environment.",
                status_code=500,
            )
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized | model=%s", _MODEL)
    return _client


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _read_file_bytes(file_path: str) -> bytes:
    """Read prescription file bytes from disk.

    Args:
        file_path: Relative path from project root stored in the DB.

    Returns:
        Raw bytes of the file.

    Raises:
        BadRequestException: if the file does not exist on disk.
        AppException:        on unexpected I/O error.
    """
    # Resolve absolute path from project root (where the process runs)
    abs_path = os.path.join(os.getcwd(), file_path)

    if not os.path.isfile(abs_path):
        logger.error("Prescription file not found on disk: %s", abs_path)
        raise BadRequestException(
            f"Prescription file not found. The file may have been deleted: {file_path}"
        )

    try:
        with open(abs_path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        logger.error("Failed to read prescription file '%s': %s", abs_path, exc)
        raise AppException(
            message="Failed to read prescription file.",
            status_code=500,
        ) from exc


def _build_prompt_text(symptoms: str | None) -> str:
    """Construct the user-facing text part of the multimodal prompt.

    Args:
        symptoms: Free-text symptoms from the prescription row (may be None).

    Returns:
        Prompt string describing what Gemini should do with the file.
    """
    symptoms_text = symptoms.strip() if symptoms else "Not provided"
    return (
        f"Patient reported symptoms: {symptoms_text}\n\n"
        "Analyze the prescription document above and return the JSON analysis."
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove accidental markdown code fences from Gemini output.

    Even with ``response_mime_type='application/json'`` set, some model
    responses include ``` fences.  This is a belt-and-suspenders safeguard.

    Args:
        text: Raw text from Gemini response.

    Returns:
        Cleaned text with fences removed.
    """
    # Remove ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return cleaned.strip()


def _parse_gemini_response(raw_text: str) -> GeminiAnalysisResult:
    """Parse and validate the raw Gemini response string.

    Args:
        raw_text: Raw text returned by the Gemini API.

    Returns:
        Validated ``GeminiAnalysisResult`` instance.

    Raises:
        AppException(500): if the response is not valid JSON.
        AppException(500): if the JSON does not match the expected schema.
    """
    cleaned = _strip_markdown_fences(raw_text)

    try:
        parsed_dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(
            "Gemini returned non-JSON response. Raw text (first 500 chars): %.500s",
            raw_text,
        )
        raise AppException(
            message="AI service returned an invalid response. Please try again.",
            status_code=500,
            error="AI_INVALID_RESPONSE",
        ) from exc

    try:
        return GeminiAnalysisResult.model_validate(parsed_dict)
    except ValidationError as exc:
        logger.error(
            "Gemini JSON failed schema validation: %s | dict=%s",
            exc,
            parsed_dict,
        )
        raise AppException(
            message="AI service returned an incomplete response. Please try again.",
            status_code=500,
            error="AI_SCHEMA_MISMATCH",
        ) from exc


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def analyze_prescription(
    file_path: str,
    file_type: str,
    symptoms: str | None,
) -> GeminiAnalysisResult:
    """Analyze a prescription file using Gemini AI.

    This is the sole public function of this module.  It is called by
    ``analysis_service.py`` and performs the full Gemini round-trip.

    Flow:
        1. Read file bytes from disk.
        2. Determine MIME type.
        3. Build multimodal content (file bytes + prompt text).
        4. Call Gemini API.
        5. Parse and validate JSON response.
        6. Return ``GeminiAnalysisResult``.

    Args:
        file_path:  Relative path from project root (from prescriptions table).
        file_type:  Lowercase file extension: pdf | jpg | jpeg | png.
        symptoms:   Optional free-text symptoms from the prescription row.

    Returns:
        Validated ``GeminiAnalysisResult`` Pydantic model.

    Raises:
        BadRequestException:    if the file does not exist on disk.
        AppException(500):      if Gemini returns invalid/incomplete JSON.
        AppException(502):      on generic Gemini API error.
        AppException(503):      if Gemini quota is exceeded.
        AppException(504):      on Gemini request timeout.
    """
    # 1. Resolve MIME type
    mime_type = _MIME_TYPES.get(file_type.lower())
    if not mime_type:
        raise BadRequestException(
            f"Unsupported file type for AI analysis: '{file_type}'. "
            "Supported types: pdf, jpg, jpeg, png."
        )

    # 2. Read file from disk
    file_bytes = _read_file_bytes(file_path)
    logger.info(
        "Gemini analysis started | file_type=%s mime=%s size=%d bytes",
        file_type,
        mime_type,
        len(file_bytes),
    )

    # 3. Build multimodal content parts
    file_part = genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
    text_part = genai_types.Part.from_text(text=_build_prompt_text(symptoms))

    # 4. Call Gemini API — translate all SDK exceptions to AppException
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL,
            contents=[file_part, text_part],
            config=_GENERATION_CONFIG,
        )
    except google_exceptions.DeadlineExceeded as exc:
        logger.error("Gemini request timed out: %s", exc)
        raise AppException(
            message="AI service request timed out. Please try again.",
            status_code=504,
            error="AI_TIMEOUT",
        ) from exc
    except google_exceptions.ResourceExhausted as exc:
        logger.error("Gemini quota exceeded: %s", exc)
        raise AppException(
            message="AI service quota exceeded. Please try again later.",
            status_code=503,
            error="SERVICE_UNAVAILABLE",
        ) from exc
    except google_exceptions.ServiceUnavailable as exc:
        logger.error("Gemini service unavailable: %s", exc)
        raise AppException(
            message="AI service is temporarily unavailable. Please try again later.",
            status_code=503,
            error="SERVICE_UNAVAILABLE",
        ) from exc
    except google_exceptions.GoogleAPIError as exc:
        logger.error("Gemini API error: %s", exc)
        raise AppException(
            message="AI service encountered an error. Please try again.",
            status_code=502,
            error="AI_SERVICE_ERROR",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error calling Gemini: %s", exc)
        raise AppException(
            message="An unexpected error occurred while contacting the AI service.",
            status_code=500,
            error="AI_UNEXPECTED_ERROR",
        ) from exc

    # 5. Extract text from response
    raw_text = response.text
    if not raw_text or not raw_text.strip():
        logger.error("Gemini returned an empty response for file: %s", file_path)
        raise AppException(
            message="AI service returned an empty response. Please try again.",
            status_code=500,
            error="AI_EMPTY_RESPONSE",
        )

    logger.info("Gemini response received | length=%d chars", len(raw_text))

    # 6. Parse, validate, and return
    result = _parse_gemini_response(raw_text)
    logger.info(
        "Gemini analysis completed | disease=%s medicines_count=%d",
        result.disease_detected,
        len(result.medicines),
    )
    return result

