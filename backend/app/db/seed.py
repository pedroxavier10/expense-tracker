"""Initial data seed.

Run with: `python -m app.db.seed`

Idempotent: running it multiple times will not duplicate data. Safe to
include in container startup scripts.

With Google sign-in enabled nothing is seeded — users are created on their
first sign-in. In dev mode the dev-login user is created up front.
"""

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine
from app.services import user_service


def seed_dev_user(session: Session) -> None:
    """Create the dev-login user (with default categories) if dev login is on."""
    settings = get_settings()
    if settings.google_auth_enabled:
        print("Google sign-in enabled: no user to seed.")
        return
    user = user_service.get_or_create_dev_user(session, settings.dev_user_email)
    print(f"Dev user ready: {user.email}")


def main() -> None:
    with Session(engine) as session:
        seed_dev_user(session)
    print("Seed complete.")


if __name__ == "__main__":
    main()
