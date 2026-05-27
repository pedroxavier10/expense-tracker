from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Numeric
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.category import Category


class RecurringExpense(SQLModel, table=True):
    """A recurring expense rule. The scheduler uses this to create Expense
    entries on the first day of each month, dating them to `day_of_month`
    (clamped to the last day of that month when necessary)."""

    __tablename__ = "recurring_expenses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    category_id: UUID = Field(foreign_key="categories.id", index=True)

    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    description: str = Field(max_length=500)
    day_of_month: int = Field(ge=1, le=31)

    is_active: bool = Field(default=True)
    end_date: date | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    category: "Category" = Relationship()
