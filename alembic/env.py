"""Alembic environment configuration.

This file is called by Alembic on every `alembic` CLI command.
It does two things:
  1. Reads the database URL from our app settings (so we never hardcode it).
  2. Passes the ORM metadata to Alembic so it can auto-generate migrations
     by comparing the current DB schema with our SQLAlchemy models.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Import our app objects --------------------------------------------------
# We must import Base AND all models so Alembic sees the full metadata.
from app.database.base import Base
from app.models.user_model import User  # noqa: F401  — registers table in metadata
from app.models.prescription_model import Prescription  # noqa: F401  — registers table in metadata
from app.utils.config import get_settings

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the database URL from our settings so alembic.ini stays blank
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# The metadata Alembic uses for --autogenerate comparisons
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations (alembic upgrade head --sql)
# Generates raw SQL without connecting to the DB — useful for DBAs.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,      # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (alembic upgrade head)
# Connects to the DB and applies migrations directly.
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no persistent connections during migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
