"""AIAnalysis ORM model.

Stores the structured result of a Gemini AI analysis for a single prescription.

Design Decisions
----------------
- One-to-one with ``prescriptions`` enforced via UNIQUE constraint on
  ``prescription_id`` at both the DB and ORM level.
- ``doctor_advice`` and ``lifestyle_changes`` are stored as JSON-serialized
  TEXT strings (e.g. '["Take after meals", "Drink water"]').  Serialization /
  deserialization is handled at the schema (Pydantic) layer so the ORM layer
  stays clean and SQLite-compatible for testing.
- ``raw_response`` is a full audit trail of what Gemini returned.  It is never
  exposed directly to the HTTP layer.
- ``analysis_status`` lifecycle: pending → processing → completed | failed.
  The service layer is the sole writer of this field.

Columns
-------
id                  Auto-increment primary key.
prescription_id     FK → prescriptions.id (CASCADE on delete).  UNIQUE.
disease_detected    Free-text disease(s) identified by Gemini.
doctor_advice       JSON-serialized list of advice strings.
lifestyle_changes   JSON-serialized list of lifestyle recommendation strings.
raw_response        Complete raw JSON string returned by Gemini (LONGTEXT).
analysis_status     Lifecycle flag: pending | processing | completed | failed.
created_at          Row creation timestamp (UTC).
updated_at          Row last-modified timestamp (UTC).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AIAnalysis(Base):
    """Represents the AI-generated analysis result for a single prescription."""

    __tablename__ = "ai_analysis"

    __table_args__ = (
        UniqueConstraint(
            "prescription_id",
            name="uq_ai_analysis_prescription_id",
        ),
        {"comment": "Stores Gemini AI analysis results — one row per prescription."},
    )

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
    # Foreign key — prescription ownership
    # ------------------------------------------------------------------
    prescription_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to prescriptions.id.  UNIQUE — one analysis per prescription.",
    )

    # ------------------------------------------------------------------
    # AI-generated content
    # ------------------------------------------------------------------
    disease_detected: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Disease(s) identified by Gemini from the prescription.",
    )
    doctor_advice: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized list of doctor advice strings.",
    )
    lifestyle_changes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized list of lifestyle recommendation strings.",
    )

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------
    raw_response: Mapped[str | None] = mapped_column(
        Text().with_variant(
            # MySQL: use LONGTEXT to accommodate large Gemini payloads
            Text(length=4294967295),
            "mysql",
        ),
        nullable=True,
        comment="Complete raw JSON string returned by Gemini.  Never exposed to HTTP layer.",
    )

    # ------------------------------------------------------------------
    # Lifecycle status
    # ------------------------------------------------------------------
    analysis_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        comment="pending | processing | completed | failed",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="UTC timestamp when the analysis row was first created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="UTC timestamp of the last status or content update.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    prescription: Mapped["Prescription"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Prescription",
        back_populates="analysis",
        lazy="select",
    )

    medicines: Mapped[list["Medicine"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Medicine",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Repr — never log raw_response (can be large / sensitive)
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<AIAnalysis id={self.id!r} "
            f"prescription_id={self.prescription_id!r} "
            f"status={self.analysis_status!r}>"
        )

