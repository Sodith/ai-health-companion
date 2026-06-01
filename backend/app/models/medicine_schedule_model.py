"""Medicine Schedule ORM model.

Represents an active medicine course that a user is taking, derived from
AI-extracted medicine data. Drives reminder generation.

Design Decisions
----------------
- Separate from ``medicines`` table (Phase 3) to avoid modifying existing
  AI extraction flow.
- Denormalizes medicine_name/dosage for fast reads without JOIN chains.
- ``is_active`` allows early termination without data loss.
- Auto-created when AI analysis completes.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MedicineSchedule(Base):
    """A user's active medicine course with schedule metadata."""

    __tablename__ = "medicine_schedules"

    # PK
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # FK — user ownership
    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK — source medicine from AI extraction (nullable if manually created)
    medicine_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("medicines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Denormalized fields for fast access
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    reminders: Mapped[list["Reminder"]] = relationship(  # noqa: F821
        "Reminder", back_populates="schedule", lazy="select", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MedicineSchedule id={self.id} name={self.medicine_name!r} active={self.is_active}>"

