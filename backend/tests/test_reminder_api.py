"""Integration tests for Medicine Schedule & Reminder API endpoints.

Covers:
  GET  /api/v1/medicines                  — list schedules
  GET  /api/v1/medicines/history          — medication history
  GET  /api/v1/medicines/{id}             — schedule detail
  PATCH /api/v1/medicines/{id}/deactivate — stop a schedule
  GET  /api/v1/reminders/today            — today's reminders (auto-generate)
  GET  /api/v1/reminders                  — list with filters
  PATCH /api/v1/reminders/{id}/taken      — mark taken
  PATCH /api/v1/reminders/{id}/skipped    — mark skipped

All tests use the in-memory SQLite DB from conftest.py.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models.medicine_schedule_model import MedicineSchedule
from app.models.reminder_model import Reminder

SIGNUP_URL   = "/api/v1/auth/signup"
MEDICINES_URL = "/api/v1/medicines"
REMINDERS_URL = "/api/v1/reminders"
TODAY_URL     = "/api/v1/reminders/today"
HISTORY_URL   = "/api/v1/medicines/history"

USER = {"email": "med@example.com", "password": "StrongPass@123"}
USER_B = {"email": "other@example.com", "password": "StrongPass@123"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signup_and_token(client: TestClient, payload: dict = USER) -> str:
    res = client.post(SIGNUP_URL, json=payload)
    assert res.status_code == 201
    return res.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_schedule(db_session, user_id: int, **kwargs) -> MedicineSchedule:
    """Insert a MedicineSchedule directly into the test DB."""
    today = date.today()
    schedule = MedicineSchedule(
        user_id=user_id,
        medicine_id=None,
        medicine_name=kwargs.get("medicine_name", "Metformin"),
        dosage=kwargs.get("dosage", "500mg"),
        frequency=kwargs.get("frequency", "2 times daily"),
        duration_days=kwargs.get("duration_days", 7),
        notes=kwargs.get("notes", None),
        start_date=kwargs.get("start_date", today),
        end_date=kwargs.get("end_date", today + timedelta(days=7)),
        is_active=kwargs.get("is_active", True),
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def _seed_reminder(db_session, schedule_id: int, user_id: int, **kwargs) -> Reminder:
    """Insert a Reminder directly into the test DB."""
    reminder = Reminder(
        schedule_id=schedule_id,
        user_id=user_id,
        reminder_time=kwargs.get(
            "reminder_time",
            datetime.combine(date.today(), __import__("datetime").time(8, 0), tzinfo=timezone.utc),
        ),
        status=kwargs.get("status", "pending"),
        taken_at=kwargs.get("taken_at", None),
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.refresh(reminder)
    return reminder


def _get_user_id(client: TestClient, token: str) -> int:
    res = client.get("/api/v1/auth/me", headers=_auth(token))
    return res.json()["data"]["id"]


# ---------------------------------------------------------------------------
# GET /medicines
# ---------------------------------------------------------------------------

class TestListMedicines:
    def test_returns_empty_for_new_user(self, client):
        token = _signup_and_token(client)
        res = client.get(MEDICINES_URL, headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_returns_user_schedules(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        _seed_schedule(db_session, user_id, medicine_name="Aspirin")
        _seed_schedule(db_session, user_id, medicine_name="Metformin")

        res = client.get(MEDICINES_URL, headers=_auth(token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 2
        names = {d["medicine_name"] for d in data}
        assert names == {"Aspirin", "Metformin"}

    def test_no_auth_returns_401(self, client):
        res = client.get(MEDICINES_URL)
        assert res.status_code == 401

    def test_ownership_isolation(self, client, db_session):
        """User A's medicines are not visible to User B."""
        token_a = _signup_and_token(client, USER)
        token_b = _signup_and_token(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        _seed_schedule(db_session, user_a_id, medicine_name="Lisinopril")

        res = client.get(MEDICINES_URL, headers=_auth(token_b))
        assert res.json()["data"] == []


# ---------------------------------------------------------------------------
# GET /medicines/{id}
# ---------------------------------------------------------------------------

class TestGetMedicine:
    def test_returns_detail(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)

        res = client.get(f"{MEDICINES_URL}/{schedule.id}", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == schedule.id
        assert data["medicine_name"] == "Metformin"
        assert "reminders_today" in data

    def test_404_for_nonexistent(self, client):
        token = _signup_and_token(client)
        res = client.get(f"{MEDICINES_URL}/99999", headers=_auth(token))
        assert res.status_code == 404

    def test_404_for_other_users_schedule(self, client, db_session):
        token_a = _signup_and_token(client, USER)
        token_b = _signup_and_token(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        schedule = _seed_schedule(db_session, user_a_id)

        res = client.get(f"{MEDICINES_URL}/{schedule.id}", headers=_auth(token_b))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /medicines/{id}/deactivate
# ---------------------------------------------------------------------------

class TestDeactivateMedicine:
    def test_deactivates_successfully(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)

        res = client.patch(f"{MEDICINES_URL}/{schedule.id}/deactivate", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["success"] is True

        db_session.refresh(schedule)
        assert schedule.is_active is False

    def test_cannot_deactivate_other_users(self, client, db_session):
        token_a = _signup_and_token(client, USER)
        token_b = _signup_and_token(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        schedule = _seed_schedule(db_session, user_a_id)

        res = client.patch(f"{MEDICINES_URL}/{schedule.id}/deactivate", headers=_auth(token_b))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /reminders/today
# ---------------------------------------------------------------------------

class TestTodayReminders:
    def test_empty_for_no_schedules(self, client):
        token = _signup_and_token(client)
        res = client.get(TODAY_URL, headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_generates_reminders_for_active_schedule(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        _seed_schedule(db_session, user_id, frequency="2 times daily")

        res = client.get(TODAY_URL, headers=_auth(token))
        assert res.status_code == 200
        data = res.json()["data"]
        # 2 times daily → 2 reminders
        assert len(data) == 2
        statuses = {r["status"] for r in data}
        assert statuses == {"pending"}

    def test_idempotent_generation(self, client, db_session):
        """Calling today twice should not duplicate reminders."""
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        _seed_schedule(db_session, user_id, frequency="1 time daily")

        client.get(TODAY_URL, headers=_auth(token))
        res = client.get(TODAY_URL, headers=_auth(token))
        assert len(res.json()["data"]) == 1

    def test_inactive_schedule_not_included(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        _seed_schedule(db_session, user_id, is_active=False)

        res = client.get(TODAY_URL, headers=_auth(token))
        assert res.json()["data"] == []

    def test_no_auth_returns_401(self, client):
        res = client.get(TODAY_URL)
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /reminders/{id}/taken
# ---------------------------------------------------------------------------

class TestMarkTaken:
    def test_marks_pending_reminder_as_taken(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        reminder = _seed_reminder(db_session, schedule.id, user_id)

        res = client.patch(f"{REMINDERS_URL}/{reminder.id}/taken", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "taken"
        assert data["taken_at"] is not None

    def test_cannot_mark_already_taken(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        reminder = _seed_reminder(db_session, schedule.id, user_id, status="taken")

        res = client.patch(f"{REMINDERS_URL}/{reminder.id}/taken", headers=_auth(token))
        assert res.status_code == 400

    def test_404_for_nonexistent_reminder(self, client):
        token = _signup_and_token(client)
        res = client.patch(f"{REMINDERS_URL}/99999/taken", headers=_auth(token))
        assert res.status_code == 404

    def test_cannot_mark_other_users_reminder(self, client, db_session):
        token_a = _signup_and_token(client, USER)
        token_b = _signup_and_token(client, USER_B)
        user_a_id = _get_user_id(client, token_a)
        schedule = _seed_schedule(db_session, user_a_id)
        reminder = _seed_reminder(db_session, schedule.id, user_a_id)

        res = client.patch(f"{REMINDERS_URL}/{reminder.id}/taken", headers=_auth(token_b))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /reminders/{id}/skipped
# ---------------------------------------------------------------------------

class TestMarkSkipped:
    def test_marks_pending_reminder_as_skipped(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        reminder = _seed_reminder(db_session, schedule.id, user_id)

        res = client.patch(f"{REMINDERS_URL}/{reminder.id}/skipped", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "skipped"

    def test_cannot_mark_already_skipped(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        reminder = _seed_reminder(db_session, schedule.id, user_id, status="skipped")

        res = client.patch(f"{REMINDERS_URL}/{reminder.id}/skipped", headers=_auth(token))
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# GET /reminders (filterable)
# ---------------------------------------------------------------------------

class TestListReminders:
    def test_filter_by_status_pending(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        _seed_reminder(db_session, schedule.id, user_id, status="pending")
        _seed_reminder(
            db_session, schedule.id, user_id,
            status="taken",
            reminder_time=datetime.combine(
                date.today(), __import__("datetime").time(20, 0), tzinfo=timezone.utc
            ),
        )

        res = client.get(f"{REMINDERS_URL}?status=pending", headers=_auth(token))
        data = res.json()["data"]
        assert all(r["status"] == "pending" for r in data)

    def test_filter_by_date(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)
        yesterday = date.today() - timedelta(days=1)
        _seed_reminder(
            db_session, schedule.id, user_id,
            reminder_time=datetime.combine(
                yesterday, __import__("datetime").time(8, 0), tzinfo=timezone.utc
            ),
            status="taken",
        )

        res = client.get(
            f"{REMINDERS_URL}?date={yesterday.isoformat()}",
            headers=_auth(token),
        )
        data = res.json()["data"]
        assert len(data) == 1
        assert yesterday.isoformat() in data[0]["reminder_time"]


# ---------------------------------------------------------------------------
# GET /medicines/history
# ---------------------------------------------------------------------------

class TestMedicineHistory:
    def test_empty_for_no_history(self, client):
        token = _signup_and_token(client)
        res = client.get(HISTORY_URL, headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_returns_taken_and_skipped_only(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)

        yesterday = date.today() - timedelta(days=1)
        _seed_reminder(
            db_session, schedule.id, user_id, status="taken",
            reminder_time=datetime.combine(
                yesterday, __import__("datetime").time(8, 0), tzinfo=timezone.utc
            ),
        )
        _seed_reminder(
            db_session, schedule.id, user_id, status="pending",
            reminder_time=datetime.combine(
                date.today(), __import__("datetime").time(8, 0), tzinfo=timezone.utc
            ),
        )

        res = client.get(f"{HISTORY_URL}?days=7", headers=_auth(token))
        data = res.json()["data"]
        # Only the 'taken' reminder should appear — pending is excluded
        all_reminders = [r for day in data for r in day["reminders"]]
        assert all(r["status"] in ("taken", "skipped") for r in all_reminders)
        assert len(all_reminders) == 1

    def test_days_filter(self, client, db_session):
        token = _signup_and_token(client)
        user_id = _get_user_id(client, token)
        schedule = _seed_schedule(db_session, user_id)

        old_date = date.today() - timedelta(days=10)
        _seed_reminder(
            db_session, schedule.id, user_id, status="taken",
            reminder_time=datetime.combine(
                old_date, __import__("datetime").time(8, 0), tzinfo=timezone.utc
            ),
        )

        # Should NOT appear in 7-day history
        res = client.get(f"{HISTORY_URL}?days=7", headers=_auth(token))
        all_reminders = [r for day in res.json()["data"] for r in day["reminders"]]
        assert len(all_reminders) == 0

