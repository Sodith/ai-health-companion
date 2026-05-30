"""SQLAlchemy ORM models.

Import all models here so that Alembic's autogenerate can discover every
table when it inspects Base.metadata.
"""

from app.models.user_model import User  # noqa: F401
from app.models.prescription_model import Prescription  # noqa: F401

__all__ = ["User", "Prescription"]
