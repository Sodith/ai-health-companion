"""Reminder ORM model.

Represents a single dose reminder at a specific date+time.
Generated lazily (daily) from active MedicineSchedule records.

Design Decisions
----------------
- Denormalized ``user_id`` for fast per-user queries without JOINs.
- UNIQUE constraint on (schedule_id, reminder_time) prevents duplicate generation.
- ``taken_at`` records the actual moment user acknowledged the reminder.
- Status enum kept as String for DB portability (SQLite in tests).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Reminder(Base):
    """A single dose reminder for a medicine schedule."""

    __tablename__ = "reminders"

    __table_args__ = (
        UniqueConstraint("schedule_id", "reminder_time", name="uq_reminders_schedule_time"),
    )

    # PK
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # FK — schedule
    schedule_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("medicine_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK — denormalized user for fast queries
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reminder details
    reminder_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    taken_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    schedule: Mapped["MedicineSchedule"] = relationship(  # noqa: F821
        "MedicineSchedule", back_populates="reminders", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} time={self.reminder_time} status={self.status!r}>"

