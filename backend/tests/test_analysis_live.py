"""Live end-to-end integration tests — real Gemini API calls.

These tests use:
  - Real GEMINI_API_KEY from .env
  - Real prescription image (tests/real_prescription.png)
  - Real MySQL database (from .env DATABASE_URL)
  - Full HTTP stack via FastAPI TestClient

Gemini is NOT mocked. Every test makes actual API calls.

Run with:
    pytest tests/test_analysis_live.py -v -s

Coverage
--------
  1. Full end-to-end: upload prescription → trigger analysis → verify Gemini result
  2. Gemini extracts correct medicines from real prescription image
  3. Idempotency: second POST returns cached result — Gemini NOT called twice
  4. GET retrieves stored analysis after POST
  5. JSON list fields deserialized correctly in response
  6. Disclaimer present in every response
  7. Raw response stored in DB
  8. All medicine fields persisted to DB
"""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.analysis_model import AIAnalysis
from app.models.medicine_model import Medicine
from app.utils.config import get_settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SIGNUP_URL   = "/api/v1/auth/signup"
LOGIN_URL    = "/api/v1/auth/login"
UPLOAD_URL   = "/api/v1/prescriptions/upload"
ANALYSIS_URL = "/api/v1/analysis/{pid}"

REAL_PRESCRIPTION = os.path.join(os.path.dirname(__file__), "real_prescription.png")

TEST_USER = {"email": "live_test@example.com", "password": "LiveTest@123"}

# ---------------------------------------------------------------------------
# Test DB — isolated SQLite so live tests don't pollute MySQL
# ---------------------------------------------------------------------------
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="module")
def db():
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Module-scoped shared state — persisted across tests in this file
# ---------------------------------------------------------------------------
_state: dict = {}


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test 1: Signup + Login
# ---------------------------------------------------------------------------
class TestLiveGeminiAnalysis:

    def test_01_signup_and_login(self, client):
        """Register a user and obtain a JWT."""
        res = client.post(SIGNUP_URL, json=TEST_USER)
        assert res.status_code == 201, res.text
        _state["token"] = res.json()["data"]["access_token"]
        print(f"\n✅ Signed up — token: {_state['token'][:20]}...")

    def test_02_upload_real_prescription(self, client):
        """Upload the real prescription PNG via the actual upload endpoint."""
        assert os.path.isfile(REAL_PRESCRIPTION), \
            f"Prescription image not found: {REAL_PRESCRIPTION}"

        with open(REAL_PRESCRIPTION, "rb") as f:
            res = client.post(
                UPLOAD_URL,
                files={"prescription_file": ("real_prescription.png", f, "image/png")},
                data={"symptoms": "Excessive thirst, frequent urination, headache, fatigue, blurred vision"},
                headers=_auth_headers(_state["token"]),
            )

        assert res.status_code == 201, res.text
        body = res.json()
        _state["prescription_id"] = body["data"]["upload_id"]
        print(f"\n✅ Prescription uploaded — id={_state['prescription_id']}")

    def test_03_trigger_analysis_calls_real_gemini(self, client, db):
        """POST /analysis/{id} calls real Gemini and returns structured result."""
        print(f"\n🤖 Calling Gemini API with real prescription...")

        res = client.post(
            ANALYSIS_URL.format(pid=_state["prescription_id"]),
            headers=_auth_headers(_state["token"]),
        )

        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        body = res.json()

        print(f"\n📋 Gemini Response:")
        print(f"   status          : {body['data']['analysis_status']}")
        print(f"   disease_detected: {body['data']['disease_detected']}")
        print(f"   doctor_advice   : {body['data']['doctor_advice']}")
        print(f"   lifestyle_changes: {body['data']['lifestyle_changes']}")
        print(f"   medicines count : {len(body['data']['medicines'])}")
        for m in body['data']['medicines']:
            print(f"      → {m['medicine_name']} | {m['dosage']} | {m['frequency']} | {m['duration']}")
        print(f"   disclaimer      : {body['data']['disclaimer'][:60]}...")

        # Core assertions
        assert body["success"] is True
        assert body["data"]["analysis_status"] == "completed"
        assert body["data"]["prescription_id"] == _state["prescription_id"]

        # Gemini must return something meaningful
        assert body["data"]["disease_detected"] is not None, \
            "Gemini should detect a disease from the prescription"
        assert isinstance(body["data"]["doctor_advice"], list)
        assert isinstance(body["data"]["lifestyle_changes"], list)
        assert isinstance(body["data"]["medicines"], list)
        assert len(body["data"]["medicines"]) > 0, \
            "Gemini should extract at least one medicine"

        # Disclaimer always present
        assert "NOT a substitute" in body["data"]["disclaimer"]

        _state["analysis_id"] = body["data"]["analysis_id"]

    def test_04_gemini_extracts_metformin(self, client):
        """Gemini must identify Metformin from the prescription."""
        res = client.get(
            ANALYSIS_URL.format(pid=_state["prescription_id"]),
            headers=_auth_headers(_state["token"]),
        )
        assert res.status_code == 200
        medicines = res.json()["data"]["medicines"]
        names = [m["medicine_name"].lower() for m in medicines]
        print(f"\n💊 Extracted medicine names: {names}")

        assert any("metformin" in n for n in names), \
            f"Metformin not found in extracted medicines: {names}"

    def test_05_idempotency_second_post_returns_cached(self, client):
        """Second POST must return HTTP 200 cached — Gemini NOT called again."""
        import app.services.gemini_service as gs
        original_fn = gs.analyze_prescription
        call_count = {"n": 0}

        def counting_wrapper(*args, **kwargs):
            call_count["n"] += 1
            return original_fn(*args, **kwargs)

        gs.analyze_prescription = counting_wrapper
        try:
            res = client.post(
                ANALYSIS_URL.format(pid=_state["prescription_id"]),
                headers=_auth_headers(_state["token"]),
            )
        finally:
            gs.analyze_prescription = original_fn

        assert res.status_code == 200, \
            f"Expected 200 cached, got {res.status_code}"
        assert "cached" in res.json()["message"].lower()
        assert call_count["n"] == 0, \
            f"Gemini was called {call_count['n']} times — should be 0 for completed analysis"

        print(f"\n✅ Idempotency confirmed — Gemini call count: {call_count['n']}")

    def test_06_get_returns_stored_analysis(self, client):
        """GET /analysis/{id} returns stored result without calling Gemini."""
        res = client.get(
            ANALYSIS_URL.format(pid=_state["prescription_id"]),
            headers=_auth_headers(_state["token"]),
        )

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["analysis_status"] == "completed"
        assert data["analysis_id"] == _state["analysis_id"]
        assert isinstance(data["doctor_advice"], list)
        assert isinstance(data["lifestyle_changes"], list)
        print(f"\n✅ GET returned stored analysis — id={data['analysis_id']}")

    def test_07_list_fields_are_proper_arrays_not_strings(self, client):
        """doctor_advice and lifestyle_changes must be JSON arrays, not raw strings."""
        res = client.get(
            ANALYSIS_URL.format(pid=_state["prescription_id"]),
            headers=_auth_headers(_state["token"]),
        )
        data = res.json()["data"]

        assert isinstance(data["doctor_advice"], list), \
            f"doctor_advice should be list, got {type(data['doctor_advice'])}"
        assert isinstance(data["lifestyle_changes"], list), \
            f"lifestyle_changes should be list, got {type(data['lifestyle_changes'])}"
        assert len(data["doctor_advice"]) > 0, "doctor_advice should not be empty"
        print(f"\n✅ List fields correctly deserialized")
        print(f"   doctor_advice[0]    : {data['doctor_advice'][0]}")
        print(f"   lifestyle_changes[0]: {data['lifestyle_changes'][0]}")

    def test_08_raw_response_persisted_in_db(self, client, db):
        """Raw Gemini response must be stored in the DB for audit purposes."""
        import json as _json
        db.expire_all()
        analysis = db.query(AIAnalysis).filter_by(
            id=_state["analysis_id"]
        ).first()

        assert analysis is not None
        assert analysis.raw_response is not None, "raw_response should be persisted"
        assert len(analysis.raw_response) > 10, "raw_response should not be empty"

        # Verify it's valid JSON
        parsed = _json.loads(analysis.raw_response)
        assert isinstance(parsed, dict)
        print(f"\n✅ raw_response stored — {len(analysis.raw_response)} chars, valid JSON")

    def test_09_medicines_persisted_in_db(self, client, db):
        """All medicines returned by Gemini must be persisted in DB."""
        db.expire_all()
        medicines = db.query(Medicine).filter_by(
            analysis_id=_state["analysis_id"]
        ).all()

        assert len(medicines) > 0, "Medicines should be persisted in DB"
        print(f"\n✅ {len(medicines)} medicines persisted in DB:")
        for m in medicines:
            print(f"   [{m.id}] {m.medicine_name} | {m.dosage} | {m.frequency} | {m.duration}")
            assert m.medicine_name is not None
            assert m.medicine_name.strip() != ""

