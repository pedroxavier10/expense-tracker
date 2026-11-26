import calendar
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import extract
from sqlmodel import Session, select

from app.models.expense import Expense
from app.models.recurring_expense import RecurringExpense
from app.schemas.recurring_expense import RecurringExpenseCreate, RecurringExpenseUpdate


def resolve_expense_date(year: int, month: int, day_of_month: int) -> date:
    """Return the target date, clamping day_of_month to the last day of the month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day_of_month, last_day))


def get_recurring_expense(
    session: Session, user_id: UUID, rule_id: UUID
) -> RecurringExpense | None:
    rule = session.get(RecurringExpense, rule_id)
    if rule and rule.user_id == user_id:
        return rule
    return None


def list_recurring_expenses(session: Session, user_id: UUID) -> list[RecurringExpense]:
    stmt = select(RecurringExpense).where(RecurringExpense.user_id == user_id)
    return list(session.exec(stmt).all())


def create_recurring_expense(
    session: Session, user_id: UUID, data: RecurringExpenseCreate, *, commit: bool = True
) -> RecurringExpense:
    """Create a rule. With `commit=False` it is only flushed (id assigned), so a
    caller can do more work in the same transaction and commit once."""
    rule = RecurringExpense(
        user_id=user_id,
        category_id=data.category_id,
        amount=data.amount,
        description=data.description,
        day_of_month=data.day_of_month,
        is_active=data.is_active,
        end_date=data.end_date,
    )
    session.add(rule)
    if not commit:
        session.flush()
        return rule
    session.commit()
    session.refresh(rule)
    return rule


def update_recurring_expense(
    session: Session, user_id: UUID, rule_id: UUID, data: RecurringExpenseUpdate
) -> RecurringExpense | None:
    rule = get_recurring_expense(session, user_id, rule_id)
    if not rule:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.now(UTC)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def delete_recurring_expense(session: Session, user_id: UUID, rule_id: UUID) -> bool:
    rule = get_recurring_expense(session, user_id, rule_id)
    if not rule:
        return False
    session.delete(rule)
    session.commit()
    return True


def materialize_for_rule(
    session: Session, rule: RecurringExpense, year: int, month: int
) -> Expense | None:
    """Create an Expense for the given month from a recurring rule.

    Returns None if:
    - the rule is inactive
    - end_date is before the target month
    - an expense for this rule/month already exists (idempotency)
    """
    if not rule.is_active:
        return None
    if rule.end_date and rule.end_date < date(year, month, 1):
        return None

    # Idempotency check: look for an existing expense for this rule in this month.
    existing = session.exec(
        select(Expense).where(
            Expense.recurring_expense_id == rule.id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
        )
    ).first()
    if existing:
        return None

    expense_date = resolve_expense_date(year, month, rule.day_of_month)
    expense = Expense(
        user_id=rule.user_id,
        category_id=rule.category_id,
        amount=rule.amount,
        description=rule.description,
        expense_date=expense_date,
        recurring_expense_id=rule.id,
        is_recurring=True,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def materialize_all(session: Session, target_year: int, target_month: int) -> int:
    """Create expenses for all active recurring rules for the given month.

    Returns the number of expenses created.
    """
    rules = session.exec(
        select(RecurringExpense).where(RecurringExpense.is_active == True)  # noqa: E712
    ).all()
    created = 0
    for rule in rules:
        if materialize_for_rule(session, rule, target_year, target_month):
            created += 1
    return created
