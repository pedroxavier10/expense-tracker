"""Category-related business logic."""

from uuid import UUID

from sqlmodel import Session, select

from app.models.category import Category


def list_categories(session: Session) -> list[Category]:
    return list(session.exec(select(Category).order_by(Category.name)).all())


def get_category(session: Session, category_id: UUID) -> Category | None:
    return session.get(Category, category_id)


def get_category_by_slug(session: Session, slug: str) -> Category | None:
    return session.exec(select(Category).where(Category.slug == slug)).first()


def create_category(
    session: Session, slug: str, name: str, icon: str | None = None
) -> Category:
    category = Category(slug=slug, name=name, icon=icon)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category
