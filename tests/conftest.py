"""Shared pytest fixtures for the test suite.

We use an in-memory SQLite database so tests:
  - Never touch a real MySQL instance.
  - Run in full isolation — every test function gets a fresh DB.
  - Run fast with zero external dependencies.

StaticPool is critical here: without it, SQLite creates a *new* empty
database for every new connection, so the tables created in setup would
be invisible to the session used by the route handlers.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool ensures all engine connections share the same SQLite connection
# — meaning CREATE TABLE and SELECT see the same in-memory database.
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Yield a clean DB session for a single test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with the real DB session swapped for the test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
