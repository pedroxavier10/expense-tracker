"""Database engine and session management.

We use SQLModel (built on SQLAlchemy 2.0 + Pydantic) for a single source of
truth between ORM models and API schemas. Sessions are short-lived and scoped
per-request via the `get_session` FastAPI dependency.
"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

# `echo=False` keeps logs clean; flip to True for SQL debugging.
# `pool_pre_ping=True` validates connections before use, avoiding stale-connection
# errors after the database restarts.
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    with Session(engine) as session:
        yield session
