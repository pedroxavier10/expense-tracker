"""Category ORM model.

Categories are per-user: each user owns their own set and they are not shared.
A user's default categories are seeded on user creation (see
`user_service.create_user_with_defaults`). The `slug` is a stable, English,
machine-friendly identifier (used by the LLM prompt and filters); it is unique
*per user*, not globally.
"""

from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    """An expense category (e.g. food, transport, health)."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_categories_user_slug"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    # Machine-friendly stable identifier used by the LLM tools and the API.
    # Human-friendly localized labels live on the frontend. Unique per user.
    slug: str = Field(index=True, max_length=50)
    name: str = Field(max_length=100)
    # Optional emoji/icon hint for the UI.
    icon: str | None = Field(default=None, max_length=10)
    # Soft-delete flag: archived categories are hidden from new selections but
    # kept so historical expenses/reports still resolve their category.
    is_active: bool = Field(default=True, index=True)
