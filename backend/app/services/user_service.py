"""User-related business logic.

Thin service layer between the API endpoints and the database. Keeping the
logic out of the endpoint files means the same functions can be called from
other places (CLI scripts, the future LLM tool layer, tests) without HTTP
plumbing.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserUpdate


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def create_user(session: Session, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
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


def authenticate(session: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None."""
    user = get_user_by_email(session, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
