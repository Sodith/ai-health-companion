"""Integration tests for AI analysis API endpoints.

Exercises the full request → controller → service → DB stack using the
in-memory SQLite test database from conftest.py.

GeminiService is patched out in every test — we never call the real API.
File I/O (reading prescription bytes) is also patched so tests run offline.

Coverage
--------
POST /api/v1/analysis/{prescription_id}
  - Valid trigger returns 201 with full analysis structure
  - Completed analysis returns 200 cached result (Gemini NOT called again)
  - Processing analysis returns 409
  - Failed analysis is retried and returns 201
  - Wrong owner returns 403
  - Non-existent prescription returns 404
  - No auth token returns 401
  - Gemini timeout surfaces as 504
  - Gemini quota exceeded surfaces as 503
  - Gemini invalid JSON surfaces as 500
  - Missing file on disk surfaces as 400
  - Medicines are persisted correctly in DB

GET /api/v1/analysis/{prescription_id}
  - Returns stored completed analysis with 200
  - Returns stored failed analysis (never calls Gemini)
  - No analysis record returns 404
  - Wrong owner returns 403
  - Non-existent prescription returns 404
  - No auth token returns 401
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.analysis_model import AIAnalysis
from app.models.medicine_model import Medicine
from app.models.prescription_model import Prescription
from app.schemas.analysis_schema import GeminiAnalysisResult, GeminiMedicineItem
from app.utils.exceptions import AppException, BadRequestException

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------
SIGNUP_URL   = "/api/v1/auth/signup"
LOGIN_URL    = "/api/v1/auth/login"
UPLOAD_URL   = "/api/v1/prescriptions/upload"
ANALYSIS_URL = "/api/v1/analysis/{prescription_id}"

# ---------------------------------------------------------------------------
# Test users
# ---------------------------------------------------------------------------
USER_A = {"email": "usera@example.com", "password": "StrongPass@123"}
USER_B = {"email": "userb@example.com", "password": "StrongPass@123"}

# ---------------------------------------------------------------------------
# Fake Gemini response — used across all success-path tests
# ---------------------------------------------------------------------------
FAKE_GEMINI_RESULT = GeminiAnalysisResult(
    disease_detected="Type 2 Diabetes",
    doctor_advice=["Take medicines after meals", "Monitor blood sugar daily"],
    lifestyle_changes=["Walk 30 minutes daily", "Avoid sugary foods"],
    medicines=[
        GeminiMedicineItem(
            medicine_name="Metformin",
            dosage="500mg",
            frequency="2 times daily",
            duration="30 days",
            notes=None,
        ),
        GeminiMedicineItem(
            medicine_name="Glipizide",
            dosage="5mg",
            frequency="Once daily",
            duration="30 days",
            notes="Take before breakfast",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, payload: dict) -> str:
    """Register a user and return their JWT access token."""
    res = client.post(SIGNUP_URL, json=payload)
    assert res.status_code == 201
    return res.json()["data"]["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_prescription(db_session, user_id: str, symptoms: str | None = "headache") -> Prescription:
    """Insert a Prescription row directly into the test DB."""
    uid = str(uuid4())
    prescription = Prescription(
        user_id=user_id,
        original_file_name="rx.jpg",
        stored_file_name=f"{uid}.jpg",
        file_path=f"uploads/prescriptions/2026/{uid}.jpg",
        file_type="jpg",
        file_size=1024,
        symptoms=symptoms,
        upload_status="uploaded",
    )
    db_session.add(prescription)
    db_session.commit()
    db_session.refresh(prescription)
    return prescription


def _seed_analysis(
    db_session,
    prescription_id: int,
    status: str = "completed",
) -> AIAnalysis:
    """Insert an AIAnalysis row directly into the test DB."""
    analysis = AIAnalysis(
        prescription_id=prescription_id,
        disease_detected="Type 2 Diabetes",
        doctor_advice=json.dumps(["Take after meals"]),
        lifestyle_changes=json.dumps(["Walk daily"]),
        raw_response=json.dumps({}),
        analysis_status=status,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def _get_user_id(client: TestClient, token: str) -> str:
    """Return the authenticated user's ID from /auth/me."""
    res = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert res.status_code == 200
    return res.json()["data"]["id"]


# ---------------------------------------------------------------------------
# POST /analysis/{prescription_id}
# ---------------------------------------------------------------------------

class TestTriggerAnalysis:

    def test_trigger_returns_201_with_full_structure(self, client, db_session):
        """Valid trigger: returns 201, full analysis body with medicines."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            return_value=FAKE_GEMINI_RESULT,
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake-bytes"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 201
        body = res.json()
        assert body["success"] is True
        assert body["data"]["analysis_status"] == "completed"
        assert body["data"]["disease_detected"] == "Type 2 Diabetes"
        assert "Take medicines after meals" in body["data"]["doctor_advice"]
        assert "Walk 30 minutes daily" in body["data"]["lifestyle_changes"]
        assert len(body["data"]["medicines"]) == 2
        assert body["data"]["medicines"][0]["medicine_name"] == "Metformin"
        assert body["data"]["medicines"][0]["dosage"] == "500mg"
        assert body["data"]["medicines"][1]["medicine_name"] == "Glipizide"
        assert "NOT a substitute" in body["data"]["disclaimer"]
        assert body["data"]["prescription_id"] == prescription.id

    def test_trigger_persists_medicines_to_db(self, client, db_session):
        """Medicines are correctly persisted to the DB after analysis."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            return_value=FAKE_GEMINI_RESULT,
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 201

        # Verify DB directly
        analysis = db_session.query(AIAnalysis).filter_by(
            prescription_id=prescription.id
        ).first()
        assert analysis is not None
        assert analysis.analysis_status == "completed"

        medicines = db_session.query(Medicine).filter_by(
            analysis_id=analysis.id
        ).all()
        assert len(medicines) == 2
        names = {m.medicine_name for m in medicines}
        assert "Metformin" in names
        assert "Glipizide" in names

    def test_completed_analysis_returns_200_cached(self, client, db_session):
        """Second POST on a completed analysis returns 200 — Gemini NOT called."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="completed")

        with patch(
            "app.services.gemini_service.analyze_prescription"
        ) as mock_gemini:
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )
            assert mock_gemini.call_count == 0

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "cached" in body["message"].lower()
        assert body["data"]["analysis_status"] == "completed"

    def test_processing_analysis_returns_409(self, client, db_session):
        """POST when analysis is processing returns 409 Conflict."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="processing")

        res = client.post(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token),
        )

        assert res.status_code == 409
        assert res.json()["success"] is False

    def test_failed_analysis_is_retried(self, client, db_session):
        """POST on a failed analysis resets state and retries Gemini."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="failed")

        with patch(
            "app.services.gemini_service.analyze_prescription",
            return_value=FAKE_GEMINI_RESULT,
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 201
        assert res.json()["data"]["analysis_status"] == "completed"

    def test_wrong_owner_returns_403(self, client, db_session):
        """User B cannot trigger analysis on User A's prescription."""
        token_a = _register_and_login(client, USER_A)
        token_b = _register_and_login(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        prescription = _seed_prescription(db_session, user_a_id)

        res = client.post(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token_b),
        )

        assert res.status_code == 403
        assert res.json()["success"] is False

    def test_nonexistent_prescription_returns_404(self, client, db_session):
        """POST on a prescription ID that does not exist returns 404."""
        token = _register_and_login(client, USER_A)

        res = client.post(
            ANALYSIS_URL.format(prescription_id=99999),
            headers=_auth_headers(token),
        )

        assert res.status_code == 404
        assert res.json()["success"] is False

    def test_no_auth_token_returns_401(self, client):
        """POST without a Bearer token returns 401."""
        res = client.post(ANALYSIS_URL.format(prescription_id=1))
        assert res.status_code == 401

    def test_gemini_timeout_returns_504(self, client, db_session):
        """Gemini timeout is surfaced as HTTP 504."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            side_effect=AppException(
                message="AI service request timed out. Please try again.",
                status_code=504,
                error="AI_TIMEOUT",
            ),
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 504
        assert res.json()["error"] == "AI_TIMEOUT"

        # Verify DB row was marked failed
        db_session.expire_all()
        analysis = db_session.query(AIAnalysis).filter_by(
            prescription_id=prescription.id
        ).first()
        assert analysis.analysis_status == "failed"

    def test_gemini_quota_exceeded_returns_503(self, client, db_session):
        """Gemini quota exceeded is surfaced as HTTP 503."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            side_effect=AppException(
                message="AI service quota exceeded. Please try again later.",
                status_code=503,
                error="SERVICE_UNAVAILABLE",
            ),
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 503
        assert res.json()["error"] == "SERVICE_UNAVAILABLE"

    def test_gemini_invalid_json_returns_500(self, client, db_session):
        """Gemini returning invalid JSON is surfaced as HTTP 500."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            side_effect=AppException(
                message="AI service returned an invalid response. Please try again.",
                status_code=500,
                error="AI_INVALID_RESPONSE",
            ),
        ), patch("os.path.isfile", return_value=True), \
           patch("builtins.open", MagicMock(
               return_value=MagicMock(
                   __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"fake"))),
                   __exit__=MagicMock(return_value=False),
               )
           )):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 500
        assert res.json()["error"] == "AI_INVALID_RESPONSE"

    def test_missing_file_on_disk_returns_400(self, client, db_session):
        """If the prescription file is missing from disk, returns 400."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        with patch(
            "app.services.gemini_service.analyze_prescription",
            side_effect=BadRequestException(
                "Prescription file not found. The file may have been deleted."
            ),
        ):
            res = client.post(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )

        assert res.status_code == 400
        assert res.json()["success"] is False


# ---------------------------------------------------------------------------
# GET /analysis/{prescription_id}
# ---------------------------------------------------------------------------

class TestGetAnalysis:

    def test_get_completed_analysis_returns_200(self, client, db_session):
        """GET returns the stored completed analysis with correct structure."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="completed")

        res = client.get(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token),
        )

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["message"] == "Analysis retrieved successfully."
        assert body["data"]["analysis_status"] == "completed"
        assert body["data"]["disease_detected"] == "Type 2 Diabetes"
        assert body["data"]["doctor_advice"] == ["Take after meals"]
        assert body["data"]["lifestyle_changes"] == ["Walk daily"]
        assert "NOT a substitute" in body["data"]["disclaimer"]

    def test_get_failed_analysis_returns_200_without_gemini(self, client, db_session):
        """GET on a failed analysis returns 200 — never calls Gemini."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="failed")

        with patch(
            "app.services.gemini_service.analyze_prescription"
        ) as mock_gemini:
            res = client.get(
                ANALYSIS_URL.format(prescription_id=prescription.id),
                headers=_auth_headers(token),
            )
            assert mock_gemini.call_count == 0

        assert res.status_code == 200
        assert res.json()["data"]["analysis_status"] == "failed"

    def test_get_no_analysis_returns_404(self, client, db_session):
        """GET when no analysis has been run yet returns 404."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)

        res = client.get(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token),
        )

        assert res.status_code == 404
        assert res.json()["success"] is False

    def test_get_wrong_owner_returns_403(self, client, db_session):
        """User B cannot retrieve User A's analysis."""
        token_a = _register_and_login(client, USER_A)
        token_b = _register_and_login(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        prescription = _seed_prescription(db_session, user_a_id)
        _seed_analysis(db_session, prescription.id)

        res = client.get(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token_b),
        )

        assert res.status_code == 403
        assert res.json()["success"] is False

    def test_get_nonexistent_prescription_returns_404(self, client, db_session):
        """GET for a prescription that never existed returns 404."""
        token = _register_and_login(client, USER_A)

        res = client.get(
            ANALYSIS_URL.format(prescription_id=99999),
            headers=_auth_headers(token),
        )

        assert res.status_code == 404

    def test_get_no_auth_token_returns_401(self, client):
        """GET without a Bearer token returns 401."""
        res = client.get(ANALYSIS_URL.format(prescription_id=1))
        assert res.status_code == 401

    def test_get_with_medicines_returns_nested_list(self, client, db_session):
        """GET includes nested medicines list when present."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        analysis = _seed_analysis(db_session, prescription.id, status="completed")

        # Seed medicines directly
        db_session.add(Medicine(
            analysis_id=analysis.id,
            medicine_name="Metformin",
            dosage="500mg",
            frequency="2 times daily",
            duration="30 days",
            notes=None,
        ))
        db_session.commit()

        res = client.get(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token),
        )

        assert res.status_code == 200
        medicines = res.json()["data"]["medicines"]
        assert len(medicines) == 1
        assert medicines[0]["medicine_name"] == "Metformin"
        assert medicines[0]["dosage"] == "500mg"
        assert medicines[0]["notes"] is None

    def test_get_response_json_serializes_list_fields(self, client, db_session):
        """doctor_advice and lifestyle_changes are proper arrays — not raw JSON strings."""
        token = _register_and_login(client, USER_A)
        user_id = _get_user_id(client, token)
        prescription = _seed_prescription(db_session, user_id)
        _seed_analysis(db_session, prescription.id, status="completed")

        res = client.get(
            ANALYSIS_URL.format(prescription_id=prescription.id),
            headers=_auth_headers(token),
        )

        assert res.status_code == 200
        data = res.json()["data"]
        # Must be a list, not a JSON string
        assert isinstance(data["doctor_advice"], list)
        assert isinstance(data["lifestyle_changes"], list)
        assert data["doctor_advice"][0] == "Take after meals"

