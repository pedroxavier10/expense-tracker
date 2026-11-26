"""Expense API schemas.

Includes both the standard CRUD shapes and a `ExpenseFilters` model used by
the list endpoint. Centralizing filters in a Pydantic model makes them easy
to reuse from the future LLM tool layer (the LLM emits a filter object;
the same code path executes the query).
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryRead
from app.schemas.recurring_suggestion import RecurringSuggestionRead


class ExpenseBase(BaseModel):
    """Fields shared by create and update."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expense_date: date
    description: str = Field(min_length=1, max_length=500)
    category_id: UUID


class ExpenseCreate(ExpenseBase):
    """Payload for creating an expense."""


class ExpenseUpdate(BaseModel):
    """Payload for partial expense update. All fields optional."""

    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expense_date: date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category_id: UUID | None = None


class ExpenseRead(BaseModel):
    """Public representation of an expense, with the category embedded."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    expense_date: date
    description: str
    category: CategoryRead
    is_recurring: bool
    recurring_expense_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ExpenseCreateResult(ExpenseRead):
    """Response of POST /expenses: the expense plus, when this expense completes
    a monthly pattern, a suggestion to turn it into a recurring rule."""

    recurring_suggestion: RecurringSuggestionRead | None = None


class ExpenseFilters(BaseModel):
    """Filter parameters for listing expenses.

    Reusable: both the REST list endpoint and the future LLM `search_expenses`
    tool consume this same model.
    """

    category_id: UUID | None = None
    category_slug: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    # YYYY-MM convenience filter. Mutually exclusive with date_from / date_to.
    month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    description_contains: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ExpenseFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        if self.month and (self.date_from or self.date_to):
            raise ValueError("month cannot be combined with date_from / date_to")
        return self


class ExpenseListResponse(BaseModel):
    """Paginated list response."""

    items: list[ExpenseRead]
    total: int
    limit: int
    offset: int


# ---------- Aggregate / summary schemas ----------


class CategorySummary(BaseModel):
    category_id: str
    slug: str
    name: str
    icon: str | None
    total: Decimal
    count: int


class MonthlySummaryResponse(BaseModel):
    month: str  # YYYY-MM
    total: Decimal
    count: int
    by_category: list[CategorySummary]


class MonthlyTotal(BaseModel):
    month: str  # YYYY-MM
    total: Decimal


class AnnualSummaryResponse(BaseModel):
    year: int
    total: Decimal
    by_month: list[MonthlyTotal]
    by_category: list[CategorySummary]
