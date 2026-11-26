"""User ORM model.

Each user owns their own categories, expenses and recurring rules. Users sign
in with Google (`google_sub` is Google's stable account id); in development a
passwordless dev login can be enabled instead. No passwords are stored.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A user of the application."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    google_sub: str | None = Field(default=None, unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    language: str = Field(default="en", max_length=8)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
