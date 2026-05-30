"""Initial data seed.

Run with: `python -m app.db.seed`

Idempotent: running it multiple times will not duplicate data. Safe to
include in container startup scripts.
"""

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine
from app.services import user_service


def seed_default_user(session: Session) -> None:
    """Create the default user (with default categories) if none exists yet."""
    settings = get_settings()
    existing = user_service.get_user_by_email(session, settings.default_user_email)
    if existing:
        print(f"Default user already exists ({settings.default_user_email}).")
        return
    user_service.create_user_with_defaults(
        session,
        email=settings.default_user_email,
        password=settings.default_user_password,
    )
    print(f"Default user created with default categories: {settings.default_user_email}")


def main() -> None:
    with Session(engine) as session:
        seed_default_user(session)
    print("Seed complete.")


if __name__ == "__main__":
    main()
