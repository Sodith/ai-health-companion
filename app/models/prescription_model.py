"""Prescription ORM model.

Stores file upload metadata for each prescription submitted by a user.

Columns
-------
id                  Auto-increment primary key.
user_id             FK → users.id (CASCADE on delete).
original_file_name  Client-supplied filename kept for display/audit only.
stored_file_name    UUID-based filename written to disk; unique across all rows.
file_path           Relative path from project root, e.g.
                    uploads/prescriptions/YYYY/MM/DD/<uuid>.<ext>
file_type           Lowercased canonical extension: pdf | jpg | jpeg | png.
file_size           Size in bytes (application enforces ≤ 10 MB).
symptoms            Free-text health notes supplied by the user (nullable).
upload_status       Lifecycle flag: uploaded | processing | processed | failed.
                    Defaults to "uploaded"; reserved for future Gemini pipeline.
created_at          Row creation timestamp (UTC).
updated_at          Row last-modified timestamp (UTC).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Prescription(Base):
    """Represents a single prescription upload belonging to a user."""

    __tablename__ = "prescriptions"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # ------------------------------------------------------------------
    # Foreign key — user ownership
    # ------------------------------------------------------------------
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # File identity
    # ------------------------------------------------------------------
    original_file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename provided by the client — never used for storage.",
    )
    stored_file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="UUID-based filename written to disk.",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Relative path from project root to the stored file.",
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Canonical lowercase extension: pdf | jpg | jpeg | png.",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes.",
    )

    # ------------------------------------------------------------------
    # User-supplied health context
    # ------------------------------------------------------------------
    symptoms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text symptoms / health notes from the user.",
    )

    # ------------------------------------------------------------------
    # Lifecycle status — future-ready for Gemini processing pipeline
    # ------------------------------------------------------------------
    upload_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="uploaded",
        server_default="uploaded",
        comment="uploaded | processing | processed | failed",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    owner: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="prescriptions",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Repr — never log file_path or symptoms in plain text
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Prescription id={self.id!r} user_id={self.user_id!r} "
            f"file_type={self.file_type!r} upload_status={self.upload_status!r}>"
        )

