"""User-related business logic.

Thin service layer between the API endpoints and the database. Keeping the
logic out of the endpoint files means the same functions can be called from
other places (CLI scripts, the future LLM tool layer, tests) without HTTP
plumbing.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.security import GoogleIdentity
from app.models.user import User
from app.schemas.user import UserUpdate


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email.lower())).first()


def get_user_by_google_sub(session: Session, google_sub: str) -> User | None:
    return session.exec(select(User).where(User.google_sub == google_sub)).first()


def create_user(session: Session, email: str, google_sub: str | None = None) -> User:
    user = User(email=email.lower(), google_sub=google_sub)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_user_with_defaults(session: Session, email: str, google_sub: str | None = None) -> User:
    """Create a user and seed their default categories.

    Use this for any new-user flow (first Google sign-in, dev login, seed).
    The default slugs are already English, so no LLM call is needed here.
    """
    # Imported lazily to avoid a circular import (category_service -> slug_service).
    from app.services import category_service

    user = create_user(session, email, google_sub)
    for slug, name, icon in category_service.DEFAULT_CATEGORIES:
        category_service.create_category(session, user.id, slug=slug, name=name, icon=icon)
    return user


def update_user(session: Session, user: User, updates: UserUpdate) -> User:
    """Apply non-None fields from `updates` to `user` and persist."""
    data = updates.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in data.items():
        setattr(user, field, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login_with_google(
    session: Session, identity: GoogleIdentity, allowed_emails: set[str]
) -> User | None:
    """Resolve (or create) the user for a verified Google identity.

    Returns None when the email is not on the allow-list or the user is
    inactive. Lookup order: Google `sub` (stable even if the email changes),
    then verified email (links a pre-existing user to their Google account),
    then a brand-new user with default categories.
    """
    if identity.email.lower() not in allowed_emails:
        return None

    user = get_user_by_google_sub(session, identity.sub)
    if user is None:
        user = get_user_by_email(session, identity.email)
        if user is None:
            return create_user_with_defaults(session, identity.email, identity.sub)
        if user.google_sub is not None:
            # Same email already linked to a different Google account: refuse.
            return None
        user.google_sub = identity.sub
        session.add(user)
        session.commit()
        session.refresh(user)

    return user if user.is_active else None


def get_or_create_dev_user(session: Session, email: str) -> User:
    """Return the dev-login user, creating it (with default categories) if needed."""
    user = get_user_by_email(session, email)
    if user is None:
        user = create_user_with_defaults(session, email)
    return user
