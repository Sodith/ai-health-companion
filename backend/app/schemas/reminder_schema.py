"""Pydantic schemas for medicine schedule and reminder endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Medicine Schedule schemas
# ---------------------------------------------------------------------------


class MedicineScheduleResponse(BaseModel):
    id: int
    medicine_id: int | None = None
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration_days: int
    notes: str | None = None
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Reminder schemas
# ---------------------------------------------------------------------------


class ReminderResponse(BaseModel):
    id: int
    schedule_id: int
    medicine_name: str
    dosage: str | None = None
    reminder_time: str
    status: str
    taken_at: str | None = None


class ReminderActionResponse(BaseModel):
    id: int
    status: str
    taken_at: str


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------


class HistoryDayResponse(BaseModel):
    date: str
    reminders: list[ReminderResponse]

