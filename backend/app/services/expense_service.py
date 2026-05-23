"""Expense business logic, including the filter query builder.

The `list_expenses` function is the single source of truth for filtering.
Both the REST endpoint and the future LLM `search_expenses` tool will call it
with an `ExpenseFilters` instance.
"""

from calendar import monthrange
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.category import Category
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseFilters, ExpenseUpdate


def _resolve_month(month: str) -> tuple[date, date]:
    """Convert a 'YYYY-MM' string into an inclusive (first_day, last_day) tuple."""
    year, mon = (int(p) for p in month.split("-"))
    last_day = monthrange(year, mon)[1]
    return date(year, mon, 1), date(year, mon, last_day)


def _apply_filters(stmt, filters: ExpenseFilters, user_id: UUID):
    """Apply ExpenseFilters to a select statement. Returns the modified statement."""
    stmt = stmt.where(Expense.user_id == user_id)

    if filters.category_id:
        stmt = stmt.where(Expense.category_id == filters.category_id)

    if filters.category_slug:
        # Join to filter by human-friendly slug (used by LLM tools).
        stmt = stmt.join(Category).where(Category.slug == filters.category_slug)

    if filters.month:
        start, end = _resolve_month(filters.month)
        stmt = stmt.where(Expense.expense_date >= start, Expense.expense_date <= end)
    else:
        if filters.date_from:
            stmt = stmt.where(Expense.expense_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Expense.expense_date <= filters.date_to)

    if filters.description_contains:
        pattern = f"%{filters.description_contains.lower()}%"
        stmt = stmt.where(func.lower(Expense.description).like(pattern))

    return stmt


def list_expenses(
    session: Session, user_id: UUID, filters: ExpenseFilters
) -> tuple[list[Expense], int]:
    """Return (items, total_count) for the given filters."""
    base = select(Expense)
    base = _apply_filters(base, filters, user_id)

    # Total count (without pagination) for client-side paging UI.
    count_stmt = select(func.count()).select_from(base.subquery())
    total = session.exec(count_stmt).one()

    items_stmt = (
        base.order_by(col(Expense.expense_date).desc(), col(Expense.created_at).desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    items = list(session.exec(items_stmt).all())
    return items, total


def get_expense(session: Session, user_id: UUID, expense_id: UUID) -> Expense | None:
    expense = session.get(Expense, expense_id)
    if expense and expense.user_id == user_id:
        return expense
    return None


def create_expense(session: Session, user_id: UUID, data: ExpenseCreate) -> Expense:
    expense = Expense(
        user_id=user_id,
        category_id=data.category_id,
        amount=data.amount,
        expense_date=data.expense_date,
        description=data.description,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def update_expense(
    session: Session, user_id: UUID, expense_id: UUID, data: ExpenseUpdate
) -> Expense | None:
    expense = get_expense(session, user_id, expense_id)
    if not expense:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    expense.updated_at = datetime.now(UTC)

    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def delete_expense(session: Session, user_id: UUID, expense_id: UUID) -> bool:
    expense = get_expense(session, user_id, expense_id)
    if not expense:
        return False
    session.delete(expense)
    session.commit()
    return True
