"""Initial data seed.

Run with: `python -m app.db.seed`

Idempotent: running it multiple times will not duplicate data. Safe to
include in container startup scripts.
"""

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine
from app.services import category_service, user_service

# (slug, display name, emoji)
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


def seed_categories(session: Session) -> None:
    """Insert default categories if they do not already exist."""
    for slug, name, icon in DEFAULT_CATEGORIES:
        existing = category_service.get_category_by_slug(session, slug)
        if existing:
            continue
        category_service.create_category(session, slug=slug, name=name, icon=icon)
    print(f"Categories seeded ({len(DEFAULT_CATEGORIES)} defaults).")


def seed_default_user(session: Session) -> None:
    """Create the default user from environment variables if none exists yet."""
    settings = get_settings()
    existing = user_service.get_user_by_email(session, settings.default_user_email)
    if existing:
        print(f"Default user already exists ({settings.default_user_email}).")
        return
    user_service.create_user(
        session,
        email=settings.default_user_email,
        password=settings.default_user_password,
    )
    print(f"Default user created: {settings.default_user_email}")


def main() -> None:
    with Session(engine) as session:
        seed_categories(session)
        seed_default_user(session)
    print("Seed complete.")


if __name__ == "__main__":
    main()
