"""Medicine Schedule & Reminder controllers.

Routes:
  GET    /medicines              List user's medicine schedules.
  GET    /medicines/{id}         Get single schedule with today's reminders.
  GET    /medicines/history      Medication history (taken/skipped).
  PATCH  /medicines/{id}/deactivate  Stop a medicine schedule.
  GET    /reminders              All reminders (filterable).
  GET    /reminders/today        Today's reminders (auto-generates).
  PATCH  /reminders/{id}/taken   Mark as taken.
  PATCH  /reminders/{id}/skipped Mark as skipped.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_model import User
from app.schemas.common_schema import APIResponse
from app.services import reminder_service

medicine_router = APIRouter(prefix="/medicines", tags=["Medicines"])
reminder_router = APIRouter(prefix="/reminders", tags=["Reminders"])


# ---------------------------------------------------------------------------
# Medicine Schedule endpoints
# ---------------------------------------------------------------------------


@medicine_router.get(
    "",
    response_model=APIResponse,
    summary="List all medicine schedules",
)
def list_medicines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedules = reminder_service.get_user_schedules(db, current_user.id)
    data = [
        {
            "id": s.id,
            "medicine_id": s.medicine_id,
            "medicine_name": s.medicine_name,
            "dosage": s.dosage,
            "frequency": s.frequency,
            "duration_days": s.duration_days,
            "notes": s.notes,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in schedules
    ]
    return APIResponse.ok(data=data, message="Medicine schedules retrieved")


@medicine_router.get(
    "/history",
    response_model=APIResponse,
    summary="Medication history",
)
def medicine_history(
    days: int = Query(default=7, ge=1, le=90),
    medicine_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = reminder_service.get_medicine_history(db, current_user.id, days, medicine_id)
    return APIResponse.ok(data=history, message="Medication history retrieved")


@medicine_router.get(
    "/{schedule_id}",
    response_model=APIResponse,
    summary="Get medicine schedule details",
)
def get_medicine(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = reminder_service.get_schedule_by_id(db, current_user.id, schedule_id)
    # Also get today's reminders for this schedule
    today_reminders = reminder_service.get_reminders(
        db, current_user.id, target_date=date.today(), status_filter=None
    )
    schedule_reminders = [r for r in today_reminders if r["schedule_id"] == schedule_id]

    data = {
        "id": schedule.id,
        "medicine_id": schedule.medicine_id,
        "medicine_name": schedule.medicine_name,
        "dosage": schedule.dosage,
        "frequency": schedule.frequency,
        "duration_days": schedule.duration_days,
        "notes": schedule.notes,
        "start_date": schedule.start_date.isoformat(),
        "end_date": schedule.end_date.isoformat(),
        "is_active": schedule.is_active,
        "reminders_today": schedule_reminders,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
    }
    return APIResponse.ok(data=data, message="Medicine schedule retrieved")


@medicine_router.patch(
    "/{schedule_id}/deactivate",
    response_model=APIResponse,
    summary="Deactivate a medicine schedule",
)
def deactivate_medicine(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder_service.deactivate_schedule(db, current_user.id, schedule_id)
    db.commit()
    return APIResponse.ok(message="Medicine schedule deactivated")


# ---------------------------------------------------------------------------
# Reminder endpoints
# ---------------------------------------------------------------------------


@reminder_router.get(
    "",
    response_model=APIResponse,
    summary="List reminders (filterable)",
)
def list_reminders(
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminders = reminder_service.get_reminders(db, current_user.id, date_filter, status_filter)
    return APIResponse.ok(data=reminders, message="Reminders retrieved")


@reminder_router.get(
    "/today",
    response_model=APIResponse,
    summary="Today's reminders (auto-generates missing)",
)
def today_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminders = reminder_service.get_today_reminders(db, current_user.id)
    db.commit()
    return APIResponse.ok(data=reminders, message="Today's reminders retrieved")


@reminder_router.patch(
    "/{reminder_id}/taken",
    response_model=APIResponse,
    summary="Mark reminder as taken",
)
def mark_taken(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = reminder_service.mark_reminder(db, current_user.id, reminder_id, "taken")
    db.commit()
    return APIResponse.ok(data=result, message="Reminder marked as taken")


@reminder_router.patch(
    "/{reminder_id}/skipped",
    response_model=APIResponse,
    summary="Mark reminder as skipped",
)
def mark_skipped(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = reminder_service.mark_reminder(db, current_user.id, reminder_id, "skipped")
    db.commit()
    return APIResponse.ok(data=result, message="Reminder marked as skipped")



