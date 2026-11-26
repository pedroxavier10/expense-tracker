"""CSV import/export API schemas.

Row errors carry a machine-readable `code` (plus the offending `value`) rather
than a sentence, so the frontend can translate them with next-intl.
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.category import CategoryRead
from app.schemas.recurring_suggestion import RecurringSuggestionRead

DuplicateMode = Literal["import", "skip"]

RowErrorCode = Literal[
    "missing_amount",
    "invalid_amount",
    "non_positive_amount",
    "too_many_decimals",
    "amount_too_large",
    "invalid_date",
    "description_too_long",
    "category_too_long",
]


class ImportRowError(BaseModel):
    """A CSV row that cannot be imported. `line` is the 1-based file line."""

    line: int
    code: RowErrorCode
    value: str = ""


class ImportPreview(BaseModel):
    """What an import would do, computed without writing anything."""

    total_rows: int
    valid_rows: int
    invalid_rows: list[ImportRowError]
    # Valid rows whose (date, amount, category) already exists for the user.
    duplicates: int
    # Category names from the CSV that do not exist yet and would be created.
    new_categories: list[str]
    # Archived categories that would be restored because the CSV uses them.
    reactivated_categories: list[str]
    total_amount: Decimal
    # True when `duplicates` reaches the confirmation threshold.
    requires_confirmation: bool
    # Rows without a category whose category was inferred from the user's
    # corrections/history (instead of falling back to "Other").
    inferred_categories: int = 0


class ImportResult(BaseModel):
    """Outcome of a committed import."""

    imported: int
    skipped_duplicates: int
    skipped_invalid: int
    created_categories: list[CategoryRead]
    # Imported expenses that now repeat monthly: candidates for recurring rules.
    recurring_suggestions: list[RecurringSuggestionRead] = []
