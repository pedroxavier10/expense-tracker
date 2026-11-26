"""Shared pytest fixtures.

Tests use an in-memory SQLite database for speed and isolation. Since SQLModel
is just SQLAlchemy under the hood and we don't use Postgres-specific features
in our queries, this works without changes. Add a Postgres-backed integration
test job to CI if you ever start using JSONB, full-text search, etc.
"""

import os

# Tests must not depend on the developer's local .env auth setup. Environment
# variables take precedence over .env, so pin dev mode before the app imports
# its settings. Tests that need Google enabled use the `use_settings` fixture.
os.environ["GOOGLE_AUTH_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

from collections.abc import Callable, Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import user_service  # noqa: E402


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


@pytest.fixture(name="use_settings")
def use_settings_fixture(client: TestClient) -> Callable[..., Settings]:
    """Override the settings the endpoints see, e.g. `use_settings(google_auth_enabled=True)`."""

    def _use(**overrides: object) -> Settings:
        settings = get_settings().model_copy(update=overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        return settings

    return _use


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


@pytest.fixture(name="make_user")
def make_user_fixture(session: Session) -> Callable[[str], tuple[User, dict[str, str]]]:
    """Factory: create a user (with default categories) and return (user, auth headers)."""

    def _make(email: str) -> tuple[User, dict[str, str]]:
        user = user_service.create_user_with_defaults(session, email=email)
        return user, headers_for(user)

    return _make


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(
    make_user: Callable[[str], tuple[User, dict[str, str]]],
) -> dict[str, str]:
    """Create a test user (with default categories) and return the auth header."""
    _, headers = make_user("test@example.com")
    return headers
