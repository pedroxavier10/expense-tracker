"""Expense ORM model.

The amount is stored as Numeric(12, 2) — never use float for money. Date is
stored as a plain DATE (not datetime) because expenses are conceptually
day-level events, and storing time-of-day would invite timezone bugs.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Numeric
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.category import Category


class Expense(SQLModel, table=True):
    """A single expense entry."""

    __tablename__ = "expenses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    category_id: UUID = Field(foreign_key="categories.id", index=True)

    # Numeric(12, 2) supports values up to 9,999,999,999.99 — plenty for a
    # personal tracker while keeping cent-level precision.
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    expense_date: date = Field(index=True)
    description: str = Field(max_length=500)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Eager-loaded relationship so `ExpenseRead.model_validate(expense)` finds
    # the embedded `category`. SQLModel/SQLAlchemy resolves this lazily on
    # access, which is fine because the API serializes once per response.
    category: "Category" = Relationship()
