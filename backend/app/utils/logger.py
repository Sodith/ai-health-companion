"""Centralized logger factory.

Every module gets its own named logger via `get_logger(__name__)`.
This way log output clearly shows which module emitted each line.

Format example:
  2026-05-30 10:00:00,000 | INFO     | app.services.auth_service | User signed up: uuid
"""

import logging
import sys


def _configure_root_logger() -> None:
    """Set up the root logger once with a clean, readable format."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,  # override any existing root handler configuration
    )

    # Silence noisy third-party loggers in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for the given module.

    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)
