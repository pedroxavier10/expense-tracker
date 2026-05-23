"""Category ORM model.

Categories are global (not per-user) for simplicity. If we ever need per-user
custom categories, add a nullable `user_id` foreign key and treat NULL as
"system category".
"""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    """An expense category (e.g. food, transport, health)."""

    __tablename__ = "categories"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Machine-friendly stable identifier used by the LLM tools and the API.
    # Human-friendly localized labels live on the frontend.
    slug: str = Field(unique=True, index=True, max_length=50)
    name: str = Field(max_length=100)
    # Optional emoji/icon hint for the UI.
    icon: str | None = Field(default=None, max_length=10)
