"""Medicine Schedule & Reminder service layer.

Handles:
- Creating schedules from AI-extracted medicines.
- Lazy daily reminder generation.
- Marking reminders as taken/skipped.
- History queries.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.medicine_model import Medicine
from app.models.medicine_schedule_model import MedicineSchedule
from app.models.reminder_model import Reminder
from app.utils.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Frequency & Duration parsing
# ---------------------------------------------------------------------------

REMINDER_TIMES: dict[int, list[time]] = {
    1: [time(8, 0)],
    2: [time(8, 0), time(20, 0)],
    3: [time(8, 0), time(14, 0), time(21, 0)],
    4: [time(8, 0), time(12, 0), time(17, 0), time(22, 0)],
}


def parse_frequency(frequency: str | None) -> int:
    """Extract doses-per-day from free-text frequency string."""
    if not frequency:
        return 1
    text = frequency.lower()
    if "4" in text or "four" in text:
        return 4
    if "3" in text or "three" in text or "thrice" in text:
        return 3
    if "2" in text or "two" in text or "twice" in text or "bid" in text:
        return 2
    return 1


def parse_duration_days(duration: str | None) -> int:
    """Extract number of days from duration string. Default: 7."""
    if not duration:
        return 7
    text = duration.lower().strip()
    # Try to extract a number
    match = re.search(r"(\d+)", text)
    if not match:
        return 7
    num = int(match.group(1))
    if "week" in text:
        return num * 7
    if "month" in text:
        return num * 30
    # Default assume days
    return num


# ---------------------------------------------------------------------------
# Schedule creation (called after AI analysis completes)
# ---------------------------------------------------------------------------


def create_schedules_from_analysis(
    db: Session, user_id: str, analysis_id: int
) -> list[MedicineSchedule]:
    """Auto-create medicine schedules from all medicines in an analysis.

    Idempotent: skips medicines that already have a schedule for this user.
    """
    medicines = db.query(Medicine).filter(Medicine.analysis_id == analysis_id).all()
    if not medicines:
        return []

    # Get existing schedule medicine_ids for this user to avoid duplicates
    existing_med_ids = set(
        row[0]
        for row in db.query(MedicineSchedule.medicine_id)
        .filter(
            MedicineSchedule.user_id == user_id,
            MedicineSchedule.medicine_id.in_([m.id for m in medicines]),
        )
        .all()
    )

    schedules = []
    today = date.today()

    for med in medicines:
        if med.id in existing_med_ids:
            continue

        duration_days = parse_duration_days(med.duration)
        schedule = MedicineSchedule(
            user_id=user_id,
            medicine_id=med.id,
            medicine_name=med.medicine_name,
            dosage=med.dosage,
            frequency=med.frequency,
            duration_days=duration_days,
            notes=med.notes,
            start_date=today,
            end_date=today + timedelta(days=duration_days),
            is_active=True,
        )
        db.add(schedule)
        schedules.append(schedule)

    if schedules:
        db.flush()
        logger.info("Created %d medicine schedules for user_id=%s", len(schedules), user_id)

    return schedules


# ---------------------------------------------------------------------------
# Schedule queries
# ---------------------------------------------------------------------------


def get_user_schedules(db: Session, user_id: str) -> list[MedicineSchedule]:
    """Get all medicine schedules for a user."""
    return (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.user_id == user_id)
        .order_by(MedicineSchedule.created_at.desc())
        .all()
    )


def get_schedule_by_id(db: Session, user_id: str, schedule_id: int) -> MedicineSchedule:
    """Get a single schedule, verifying ownership."""
    schedule = (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.id == schedule_id, MedicineSchedule.user_id == user_id)
        .first()
    )
    if not schedule:
        raise NotFoundException("Medicine schedule not found")
    return schedule


def deactivate_schedule(db: Session, user_id: str, schedule_id: int) -> MedicineSchedule:
    """Deactivate a medicine schedule."""
    schedule = get_schedule_by_id(db, user_id, schedule_id)
    schedule.is_active = False
    db.flush()
    return schedule


# ---------------------------------------------------------------------------
# Reminder generation (lazy, per-day)
# ---------------------------------------------------------------------------


def _generate_reminders_for_date(
    db: Session, schedule: MedicineSchedule, target_date: date
) -> list[Reminder]:
    """Generate reminders for a specific date for one schedule."""
    if not schedule.is_active:
        return []
    if target_date < schedule.start_date or target_date > schedule.end_date:
        return []

    doses_per_day = parse_frequency(schedule.frequency)
    times = REMINDER_TIMES.get(doses_per_day, REMINDER_TIMES[1])

    reminders = []
    for t in times:
        reminder_dt = datetime.combine(target_date, t, tzinfo=timezone.utc)

        # Check if already exists (idempotency)
        exists = (
            db.query(Reminder.id)
            .filter(
                Reminder.schedule_id == schedule.id,
                Reminder.reminder_time == reminder_dt,
            )
            .first()
        )
        if exists:
            continue

        reminder = Reminder(
            schedule_id=schedule.id,
            user_id=schedule.user_id,
            reminder_time=reminder_dt,
            status="pending",
        )
        db.add(reminder)
        reminders.append(reminder)

    return reminders


def get_today_reminders(db: Session, user_id: str) -> list[dict]:
    """Get today's reminders, generating any missing ones first."""
    today = date.today()

    # Auto-deactivate expired schedules
    expired = (
        db.query(MedicineSchedule)
        .filter(
            MedicineSchedule.user_id == user_id,
            MedicineSchedule.is_active == True,  # noqa: E712
            MedicineSchedule.end_date < today,
        )
        .all()
    )
    for s in expired:
        s.is_active = False

    # Generate reminders for active schedules
    active_schedules = (
        db.query(MedicineSchedule)
        .filter(
            MedicineSchedule.user_id == user_id,
            MedicineSchedule.is_active == True,  # noqa: E712
        )
        .all()
    )

    for schedule in active_schedules:
        _generate_reminders_for_date(db, schedule, today)

    db.flush()

    # Fetch all today's reminders
    start_of_day = datetime.combine(today, time(0, 0), tzinfo=timezone.utc)
    end_of_day = datetime.combine(today, time(23, 59, 59), tzinfo=timezone.utc)

    reminders = (
        db.query(Reminder)
        .join(MedicineSchedule, Reminder.schedule_id == MedicineSchedule.id)
        .filter(
            Reminder.user_id == user_id,
            Reminder.reminder_time >= start_of_day,
            Reminder.reminder_time <= end_of_day,
        )
        .order_by(Reminder.reminder_time)
        .all()
    )

    # Enrich with medicine info — include expired schedules too
    reminder_schedule_ids = {r.schedule_id for r in reminders}
    all_schedules = (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.id.in_(reminder_schedule_ids))
        .all()
    ) if reminder_schedule_ids else []
    schedule_map = {s.id: s for s in all_schedules}
    result = []
    for r in reminders:
        sched = schedule_map.get(r.schedule_id)
        result.append({
            "id": r.id,
            "schedule_id": r.schedule_id,
            "medicine_name": sched.medicine_name if sched else "Unknown",
            "dosage": sched.dosage if sched else None,
            "reminder_time": r.reminder_time.isoformat(),
            "status": r.status,
            "taken_at": r.taken_at.isoformat() if r.taken_at else None,
        })

    return result


def get_reminders(
    db: Session, user_id: str, target_date: date | None = None, status_filter: str | None = None
) -> list[dict]:
    """Get reminders with optional date and status filters."""
    query = (
        db.query(Reminder)
        .join(MedicineSchedule, Reminder.schedule_id == MedicineSchedule.id)
        .filter(Reminder.user_id == user_id)
    )

    if target_date:
        start_of_day = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date, time(23, 59, 59), tzinfo=timezone.utc)
        query = query.filter(
            Reminder.reminder_time >= start_of_day,
            Reminder.reminder_time <= end_of_day,
        )

    if status_filter:
        query = query.filter(Reminder.status == status_filter)

    reminders = query.order_by(Reminder.reminder_time.desc()).all()

    # Build schedule map
    schedule_ids = {r.schedule_id for r in reminders}
    schedules = (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.id.in_(schedule_ids))
        .all()
    ) if schedule_ids else []
    schedule_map = {s.id: s for s in schedules}

    result = []
    for r in reminders:
        sched = schedule_map.get(r.schedule_id)
        result.append({
            "id": r.id,
            "schedule_id": r.schedule_id,
            "medicine_name": sched.medicine_name if sched else "Unknown",
            "dosage": sched.dosage if sched else None,
            "reminder_time": r.reminder_time.isoformat(),
            "status": r.status,
            "taken_at": r.taken_at.isoformat() if r.taken_at else None,
        })

    return result


# ---------------------------------------------------------------------------
# Mark reminder status
# ---------------------------------------------------------------------------


def mark_reminder(db: Session, user_id: str, reminder_id: int, new_status: str) -> dict:
    """Mark a reminder as taken or skipped."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
    if not reminder:
        raise NotFoundException("Reminder not found")

    if reminder.status != "pending":
        raise BadRequestException(f"Reminder already marked as {reminder.status}")

    now = datetime.now(timezone.utc)
    reminder.status = new_status
    reminder.taken_at = now
    db.flush()

    return {
        "id": reminder.id,
        "status": reminder.status,
        "taken_at": reminder.taken_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def get_medicine_history(
    db: Session, user_id: str, days: int = 7, medicine_id: int | None = None
) -> list[dict]:
    """Get medication history grouped by date."""
    cutoff = datetime.combine(
        date.today() - timedelta(days=days), time(0, 0), tzinfo=timezone.utc
    )

    query = (
        db.query(Reminder)
        .join(MedicineSchedule, Reminder.schedule_id == MedicineSchedule.id)
        .filter(
            Reminder.user_id == user_id,
            Reminder.status.in_(["taken", "skipped"]),
            Reminder.reminder_time >= cutoff,
        )
    )

    if medicine_id:
        query = query.filter(MedicineSchedule.id == medicine_id)

    reminders = query.order_by(Reminder.reminder_time.desc()).all()

    # Build schedule map
    schedule_ids = {r.schedule_id for r in reminders}
    schedules = (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.id.in_(schedule_ids))
        .all()
    ) if schedule_ids else []
    schedule_map = {s.id: s for s in schedules}

    # Group by date
    grouped: dict[str, list[dict]] = {}
    for r in reminders:
        sched = schedule_map.get(r.schedule_id)
        day_key = r.reminder_time.strftime("%Y-%m-%d")
        entry = {
            "id": r.id,
            "medicine_name": sched.medicine_name if sched else "Unknown",
            "dosage": sched.dosage if sched else None,
            "reminder_time": r.reminder_time.isoformat(),
            "status": r.status,
            "taken_at": r.taken_at.isoformat() if r.taken_at else None,
        }
        grouped.setdefault(day_key, []).append(entry)

    return [{"date": k, "reminders": v} for k, v in grouped.items()]

