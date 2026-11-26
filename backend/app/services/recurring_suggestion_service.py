"""Recurring-expense suggestions: spot expenses the user registers every month.

Deterministic pattern detection, no LLM. A *pattern* is the user's expenses
with the same category and the same normalized description
(`text_normalization.description_key`), not yet linked to a recurring rule,
over the last 12 calendar months. It becomes a suggestion when:

- the occurrences whose amount is within ±5% of the most recent one span at
  least `recurring_suggestion_min_months` distinct months;
- it happens about once a month (at most one extra occurrence in the window),
  so a daily coffee is never suggested;
- the most recent occurrence is in the current or the previous month;
- there is no active recurring rule for the same description and category;
- after a "No" (dismissal) only expenses registered after it count, so the
  count starts again from zero.

Suggestions are computed on demand (cheap at personal scale); only dismissals
are stored.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from statistics import median_low
from uuid import UUID

from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring_expense import RecurringExpense
from app.models.recurring_suggestion_dismissal import RecurringSuggestionDismissal
from app.schemas.recurring_expense import RecurringExpenseCreate
from app.services import category_service, recurring_expense_service
from app.services.text_normalization import description_key

LOOKBACK_MONTHS = 12
AMOUNT_TOLERANCE = Decimal("0.05")


@dataclass(frozen=True)
class RecurringSuggestion:
    pattern_key: str
    description: str
    amount: Decimal
    category: Category
    day_of_month: int
    months: int
    expenses: list[Expense]

    @property
    def expense_ids(self) -> list[UUID]:
        return [e.id for e in self.expenses]


@dataclass(frozen=True)
class AcceptResult:
    rule: RecurringExpense
    linked_expenses: int
    current_month_covered: bool


# ---------------------------------------------------------------------------
# Keys and helpers
# ---------------------------------------------------------------------------


def pattern_key(category_id: UUID, description: str) -> str | None:
    """`<category_id>:<description_key>`, or None when the description has no
    meaningful tokens (e.g. only an amount)."""
    key = description_key(description)
    return f"{category_id}:{key}" if key else None


def _parse_key(value: str) -> tuple[UUID, str] | None:
    category_part, sep, key = value.partition(":")
    if not sep or not key:
        return None
    try:
        return UUID(category_part), key
    except ValueError:
        return None


def _month_index(day: date) -> int:
    return day.year * 12 + day.month - 1


def _window_start(today: date) -> date:
    index = _month_index(today) - (LOOKBACK_MONTHS - 1)
    return date(index // 12, index % 12 + 1, 1)


def _aware_utc(value: datetime) -> datetime:
    # Datetime columns are bound/compared as timezone-aware UTC; values read back
    # from some backends may be naive, so treat naive values as UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _pattern_expenses(
    session: Session,
    user_id: UUID,
    category_id: UUID,
    key: str,
    today: date,
    created_after: datetime | None = None,
) -> list[Expense]:
    """Unlinked expenses of the pattern in the window, oldest first."""
    stmt = select(Expense).where(
        Expense.user_id == user_id,
        Expense.category_id == category_id,
        col(Expense.recurring_expense_id).is_(None),
        Expense.expense_date >= _window_start(today),
    )
    if created_after is not None:
        stmt = stmt.where(Expense.created_at > _aware_utc(created_after))
    rows = session.exec(stmt).all()
    members = [e for e in rows if description_key(e.description) == key]
    return sorted(members, key=lambda e: (e.expense_date, _aware_utc(e.created_at)))


def _same_amount(expenses: list[Expense], reference: Decimal) -> list[Expense]:
    tolerance = reference * AMOUNT_TOLERANCE
    return [e for e in expenses if abs(e.amount - reference) <= tolerance]


def _has_active_rule(session: Session, user_id: UUID, category_id: UUID, key: str) -> bool:
    rules = session.exec(
        select(RecurringExpense).where(
            RecurringExpense.user_id == user_id,
            RecurringExpense.category_id == category_id,
            RecurringExpense.is_active == True,  # noqa: E712
        )
    ).all()
    return any(description_key(r.description) == key for r in rules)


def _get_dismissal(
    session: Session, user_id: UUID, key: str
) -> RecurringSuggestionDismissal | None:
    return session.exec(
        select(RecurringSuggestionDismissal).where(
            RecurringSuggestionDismissal.user_id == user_id,
            RecurringSuggestionDismissal.pattern_key == key,
        )
    ).first()


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def find_by_key(
    session: Session, user_id: UUID, key: str, today: date | None = None
) -> RecurringSuggestion | None:
    """The suggestion for a pattern key, or None if it does not qualify (now)."""
    parsed = _parse_key(key)
    if parsed is None:
        return None
    category_id, desc_key = parsed
    category = category_service.get_category(session, user_id, category_id)
    if category is None or not category.is_active:
        return None
    if _has_active_rule(session, user_id, category_id, desc_key):
        return None

    today = today or datetime.now(UTC).date()
    dismissal = _get_dismissal(session, user_id, key)
    members = _pattern_expenses(
        session,
        user_id,
        category_id,
        desc_key,
        today,
        created_after=dismissal.dismissed_at if dismissal else None,
    )
    if not members:
        return None

    latest = members[-1]
    occurrences = _same_amount(members, latest.amount)
    months = {_month_index(e.expense_date) for e in occurrences}
    min_months = get_settings().recurring_suggestion_min_months
    if len(months) < min_months:
        return None
    if len(occurrences) > len(months) + 1:  # more than ~once a month
        return None
    if _month_index(today) - max(months) > 1:  # pattern stopped
        return None

    return RecurringSuggestion(
        pattern_key=key,
        description=latest.description,
        amount=latest.amount,
        category=category,
        day_of_month=median_low(e.expense_date.day for e in occurrences),
        months=len(months),
        expenses=occurrences,
    )


def find_for_expense(
    session: Session, user_id: UUID, expense: Expense, today: date | None = None
) -> RecurringSuggestion | None:
    """Suggestion triggered by a just-registered expense: only when that expense
    is one of the pattern's occurrences."""
    if expense.recurring_expense_id is not None:
        return None
    key = pattern_key(expense.category_id, expense.description)
    if key is None:
        return None
    suggestion = find_by_key(session, user_id, key, today)
    if suggestion is None or all(e.id != expense.id for e in suggestion.expenses):
        return None
    return suggestion


# ---------------------------------------------------------------------------
# User answers
# ---------------------------------------------------------------------------


def dismiss(session: Session, user_id: UUID, key: str) -> None:
    """Remember the "No": the pattern counts from zero again."""
    dismissal = _get_dismissal(session, user_id, key)
    if dismissal is None:
        dismissal = RecurringSuggestionDismissal(user_id=user_id, pattern_key=key)
    else:
        dismissal.dismissed_at = datetime.now(UTC)
    session.add(dismissal)
    session.commit()


def accept(
    session: Session,
    user_id: UUID,
    key: str,
    rule_in: RecurringExpenseCreate,
    today: date | None = None,
) -> AcceptResult | None:
    """Create the rule and link the pattern's past expenses to it, in one
    transaction. None if the pattern no longer qualifies as a suggestion.

    `rule_in.category_id` must already be validated as the user's own category.
    """
    today = today or datetime.now(UTC).date()
    suggestion = find_by_key(session, user_id, key, today)
    if suggestion is None:
        return None
    category_id, desc_key = suggestion.category.id, key.partition(":")[2]

    # Link every occurrence of the pattern, including those registered before
    # an earlier dismissal: they are all instances of the new rule.
    occurrences = _same_amount(
        _pattern_expenses(session, user_id, category_id, desc_key, today), suggestion.amount
    )

    rule = recurring_expense_service.create_recurring_expense(
        session, user_id, rule_in, commit=False
    )
    now = datetime.now(UTC)
    for expense in occurrences:
        expense.recurring_expense_id = rule.id
        expense.is_recurring = True
        expense.updated_at = now
        session.add(expense)
    dismissal = _get_dismissal(session, user_id, key)
    if dismissal is not None:
        session.delete(dismissal)
    session.commit()
    session.refresh(rule)

    current = _month_index(today)
    return AcceptResult(
        rule=rule,
        linked_expenses=len(occurrences),
        current_month_covered=any(_month_index(e.expense_date) == current for e in occurrences),
    )
