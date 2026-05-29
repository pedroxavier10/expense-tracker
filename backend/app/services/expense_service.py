"""Expense business logic, including the filter query builder.

The `list_expenses` function is the single source of truth for filtering.
Both the REST endpoint and the future LLM `search_expenses` tool will call it
with an `ExpenseFilters` instance.
"""

from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import extract, func
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


def get_monthly_summary(session: Session, user_id: UUID, month: str) -> dict:
    """Return total + per-category breakdown for a YYYY-MM month."""
    start, end = _resolve_month(month)
    rows = session.exec(
        select(
            Category.id,
            Category.slug,
            Category.name,
            Category.icon,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("count"),
        )
        .join(Category, Category.id == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Category.id, Category.slug, Category.name, Category.icon)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    by_category = [
        {
            "category_id": str(cid),
            "slug": slug,
            "name": name,
            "icon": icon,
            "total": str(total),
            "count": int(count),
        }
        for cid, slug, name, icon, total, count in rows
    ]
    grand_total = sum((Decimal(c["total"]) for c in by_category), Decimal("0"))
    grand_count = sum(c["count"] for c in by_category)
    return {
        "month": month,
        "total": str(grand_total),
        "count": grand_count,
        "by_category": by_category,
    }


def get_annual_summary(session: Session, user_id: UUID, year: int) -> dict:
    """Return monthly totals + category breakdown for a full calendar year.

    Two DB queries: one GROUP BY month for the bar chart, one GROUP BY category
    for the pie chart. Never fetches individual expense rows.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    # Monthly totals — GROUP BY month number (max 12 rows returned)
    monthly_rows = session.exec(
        select(
            extract("month", Expense.expense_date).label("month_num"),
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
        )
        .where(
            Expense.user_id == user_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(extract("month", Expense.expense_date))
    ).all()

    by_month_map = {int(float(month_num)): Decimal(str(total)) for month_num, total in monthly_rows}
    by_month = [
        {"month": f"{year}-{m:02d}", "total": str(by_month_map.get(m, Decimal("0")))}
        for m in range(1, 13)
    ]

    # Category totals for the full year
    cat_rows = session.exec(
        select(
            Category.id,
            Category.slug,
            Category.name,
            Category.icon,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("count"),
        )
        .join(Category, Category.id == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Category.id, Category.slug, Category.name, Category.icon)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    by_category = [
        {
            "category_id": str(cid),
            "slug": slug,
            "name": name,
            "icon": icon,
            "total": str(total),
            "count": int(count),
        }
        for cid, slug, name, icon, total, count in cat_rows
    ]
    grand_total = sum((Decimal(c["total"]) for c in by_category), Decimal("0"))

    return {
        "year": year,
        "total": str(grand_total),
        "by_month": by_month,
        "by_category": by_category,
    }


def get_top_categories(
    session: Session,
    user_id: UUID,
    date_from: date | None,
    date_to: date | None,
    limit: int,
) -> dict:
    """Return the categories with the highest total spend in the given window."""
    stmt = (
        select(
            Category.id,
            Category.slug,
            Category.name,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("count"),
        )
        .join(Category, Category.id == Expense.category_id)
        .where(Expense.user_id == user_id)
    )
    if date_from:
        stmt = stmt.where(Expense.expense_date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.expense_date <= date_to)
    stmt = (
        stmt.group_by(Category.id, Category.slug, Category.name)
        .order_by(func.sum(Expense.amount).desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    items = [
        {
            "category_id": str(cid),
            "slug": slug,
            "name": name,
            "total": str(total),
            "count": int(count),
        }
        for cid, slug, name, total, count in rows
    ]
    return {
        "from": date_from.isoformat() if date_from else None,
        "to": date_to.isoformat() if date_to else None,
        "items": items,
    }
