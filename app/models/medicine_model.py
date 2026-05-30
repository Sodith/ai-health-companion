"""Medicine ORM model.

Stores individual medicine entries extracted by Gemini AI from a prescription.
Each row belongs to exactly one AIAnalysis record.

Design Decisions
----------------
- One-to-many with ``ai_analysis``: a single prescription analysis can yield
  multiple medicines.
- All dosage / frequency / duration fields are nullable — Gemini may not always
  extract every detail from a partially legible prescription.
- ``notes`` captures any extra per-medicine context Gemini returns that does not
  fit the structured fields (e.g. "take with food", "avoid grapefruit").
- CASCADE DELETE on ``analysis_id`` FK: deleting an AIAnalysis row automatically
  removes all its medicine rows — no orphans possible.

Columns
-------
id              Auto-increment primary key.
analysis_id     FK → ai_analysis.id (CASCADE on delete).  Indexed.
medicine_name   Name of the medicine as extracted by Gemini.
dosage          Dosage string, e.g. "500mg".
frequency       Administration frequency, e.g. "2 times daily".
duration        Course duration, e.g. "30 days".
notes           Free-text extra context per medicine (nullable).
created_at      Row creation timestamp (UTC).
updated_at      Row last-modified timestamp (UTC).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Medicine(Base):
    """Represents a single medicine entry within an AI prescription analysis."""

    __tablename__ = "medicines"

    __table_args__ = {
        "comment": "Individual medicines extracted by Gemini — child of ai_analysis.",
    }

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="Surrogate primary key.",
    )

    # ------------------------------------------------------------------
    # Foreign key — analysis ownership
    # ------------------------------------------------------------------
    analysis_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("ai_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to ai_analysis.id.  Cascade-deleted when analysis is removed.",
    )

    # ------------------------------------------------------------------
    # Medicine details (all content fields nullable — partial extractions allowed)
    # ------------------------------------------------------------------
    medicine_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Medicine name as extracted by Gemini, e.g. 'Metformin'.",
    )
    dosage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Dosage string, e.g. '500mg'.",
    )
    frequency: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Administration frequency, e.g. '2 times daily'.",
    )
    duration: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Course duration, e.g. '30 days'.",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Extra per-medicine context returned by Gemini (e.g. 'take with food').",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="UTC timestamp when the medicine row was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="UTC timestamp of the last update.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    analysis: Mapped["AIAnalysis"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AIAnalysis",
        back_populates="medicines",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Medicine id={self.id!r} "
            f"analysis_id={self.analysis_id!r} "
            f"medicine_name={self.medicine_name!r} "
            f"dosage={self.dosage!r}>"
        )

