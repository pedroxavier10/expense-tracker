"""Category-related business logic.

Categories are per-user. Every function is scoped by `user_id` and verifies
ownership before returning/mutating (mirrors the expense/recurring services).
"""

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring_expense import RecurringExpense
from app.schemas.category import CategoryDeleteResult, CategoryUpdate
from app.services import slug_service

# Default categories seeded for every new user. Slugs are English on purpose
# (the LLM prompt is English); display names/icons are starting points the
# user is free to edit or delete. (slug, display name, emoji)
DEFAULT_CATEGORIES: list[tuple[str, str, str]] = [
    ("food", "Food", "🍔"),
    ("transport", "Transport", "🚗"),
    ("health", "Health", "🩺"),
    ("home", "Home", "🏠"),
    ("leisure", "Leisure", "🎮"),
    ("shopping", "Shopping", "🛍️"),
    ("work", "Work", "💼"),
    ("other", "Other", "📦"),
]


def list_categories(
    session: Session, user_id: UUID, include_inactive: bool = False
) -> list[Category]:
    stmt = select(Category).where(Category.user_id == user_id)
    if not include_inactive:
        stmt = stmt.where(Category.is_active == True)  # noqa: E712 - SQL boolean
    return list(session.exec(stmt.order_by(Category.name)).all())


def get_category(session: Session, user_id: UUID, category_id: UUID) -> Category | None:
    category = session.get(Category, category_id)
    if category and category.user_id == user_id:
        return category
    return None


def get_category_by_slug(session: Session, user_id: UUID, slug: str) -> Category | None:
    stmt = select(Category).where(
        Category.user_id == user_id, Category.slug == slug
    )
    return session.exec(stmt).first()


def create_category(
    session: Session, user_id: UUID, slug: str, name: str, icon: str | None = None
) -> Category:
    category = Category(user_id=user_id, slug=slug, name=name, icon=icon)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


async def update_category(
    session: Session, user_id: UUID, category_id: UUID, data: CategoryUpdate
) -> Category | None:
    """Rename / change icon / restore. Regenerates the slug when the name
    changes so it stays aligned (safe: expenses reference the category by id)."""
    category = get_category(session, user_id, category_id)
    if not category:
        return None

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] and updates["name"] != category.name:
        category.name = updates["name"]
        category.slug = await slug_service.generate_category_slug(
            session, user_id, category.name, exclude_category_id=category_id
        )
    if "icon" in updates:
        category.icon = updates["icon"]
    if "is_active" in updates and updates["is_active"] is not None:
        category.is_active = updates["is_active"]

    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def count_category_usage(session: Session, user_id: UUID, category_id: UUID) -> int:
    """Number of expenses + recurring rules of this user using the category."""
    expenses = session.exec(
        select(func.count())
        .select_from(Expense)
        .where(Expense.user_id == user_id, Expense.category_id == category_id)
    ).one()
    recurring = session.exec(
        select(func.count())
        .select_from(RecurringExpense)
        .where(
            RecurringExpense.user_id == user_id,
            RecurringExpense.category_id == category_id,
        )
    ).one()
    return int(expenses) + int(recurring)


def delete_or_archive_category(
    session: Session, user_id: UUID, category_id: UUID
) -> CategoryDeleteResult | None:
    """Hard-delete when unused; archive (soft-delete) when in use."""
    category = get_category(session, user_id, category_id)
    if not category:
        return None

    if count_category_usage(session, user_id, category_id) == 0:
        session.delete(category)
        session.commit()
        return CategoryDeleteResult(action="deleted", category=None)

    category.is_active = False
    session.add(category)
    session.commit()
    session.refresh(category)
    return CategoryDeleteResult(action="archived", category=category)
