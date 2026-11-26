"""Schemas for recurring-expense suggestions."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.recurring_expense import RecurringExpenseCreate, RecurringExpenseRead


class RecurringSuggestionRead(BaseModel):
    """A repeated expense that looks like it should be a recurring rule.

    `description`, `amount` and `category` come from the most recent
    occurrence; `day_of_month` is the median day of the occurrences.
    `pattern_key` identifies the pattern in the accept/dismiss calls.
    """

    model_config = ConfigDict(from_attributes=True)

    pattern_key: str
    description: str
    amount: Decimal
    category: CategoryRead
    day_of_month: int
    months: int
    expense_ids: list[UUID]


class RecurringSuggestionKey(BaseModel):
    pattern_key: str = Field(min_length=1, max_length=600)


class RecurringSuggestionAccept(RecurringSuggestionKey):
    """Accept a suggestion with the (possibly edited) rule fields."""

    rule: RecurringExpenseCreate


class RecurringSuggestionAcceptResult(BaseModel):
    rule: RecurringExpenseRead
    # Past expenses of the pattern now linked to the new rule.
    linked_expenses: int
    # True when an expense of the current month is linked, so the rule must
    # not be materialized again for this month.
    current_month_covered: bool
