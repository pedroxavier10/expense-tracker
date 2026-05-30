"""Shared pytest fixtures.

Tests use an in-memory SQLite database for speed and isolation. Since SQLModel
is just SQLAlchemy under the hood and we don't use Postgres-specific features
in our queries, this works without changes. Add a Postgres-backed integration
test job to CI if you ever start using JSONB, full-text search, etc.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_session
from app.core.security import create_access_token
from app.main import app
from app.services import user_service


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable FK enforcement in SQLite so ON DELETE SET NULL works in tests.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(session: Session) -> dict[str, str]:
    """Create a test user (with default categories) and return the auth header."""
    user = user_service.create_user_with_defaults(
        session, email="test@example.com", password="testpass123"
    )
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}
