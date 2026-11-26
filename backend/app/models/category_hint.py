"""CategoryHint ORM model — the per-user "memory" of category corrections.

When the user changes the category of an existing expense, we remember
"descriptions like this one belong to that category". Hints take precedence
over the raw expense history when suggesting a category (form pre-selection,
chat system prompt), so a single correction is enough to change future picks.

`description_key` is the normalized, order-insensitive key produced by
`text_normalization.description_key`; `description` keeps the last original
wording for display ("O que aprendi" screen, chat prompt).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlmodel import Column, Field, SQLModel


class CategoryHint(SQLModel, table=True):
    """A learned mapping: normalized description -> category, per user."""

    __tablename__ = "category_hints"
    __table_args__ = (
        UniqueConstraint("user_id", "description_key", name="uq_category_hints_user_key"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    # CASCADE: an unused category can be hard-deleted (see
    # category_service.delete_or_archive_category); its hints go with it.
    category_id: UUID = Field(
        sa_column=Column(
            "category_id",
            ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    description_key: str = Field(max_length=500)
    description: str = Field(max_length=500)

    # How many times the user corrected this description to this category.
    hit_count: int = Field(default=1)
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
