"""Database engine and session factory configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.utils.config import get_settings

settings = get_settings()

engine = create_engine(
	settings.database_url,
	pool_pre_ping=True,   # drop stale connections before use
	pool_recycle=3600,    # recycle connections after 1h to avoid MySQL 8hr timeout
	pool_size=10,         # maintain up to 10 persistent connections
	max_overflow=20,      # allow 20 extra connections under burst load
	echo=settings.app_debug,  # SQL logging only when APP_DEBUG=true
)

SessionLocal = sessionmaker(
	bind=engine,
	autoflush=False,
	autocommit=False,
	expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
	"""Yield one database session per request and close it safely."""
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

