"""RecurringSuggestionDismissal ORM model.

Recurring-expense suggestions are computed on demand from the user's expenses
(see `recurring_suggestion_service`); only the user's "No" answers are stored.
A dismissal resets the count: the pattern is suggested again only once enough
*new* months are registered after `dismissed_at`.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class RecurringSuggestionDismissal(SQLModel, table=True):
    """The user declined to turn a repeated expense pattern into a recurring rule."""

    __tablename__ = "recurring_suggestion_dismissals"
    __table_args__ = (
        UniqueConstraint("user_id", "pattern_key", name="uq_recurring_dismissals_user_key"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    # "<category_id>:<description_key>" — see recurring_suggestion_service.pattern_key.
    pattern_key: str = Field(max_length=600)
    dismissed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
