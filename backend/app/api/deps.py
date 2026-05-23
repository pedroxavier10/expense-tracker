"""Shared FastAPI dependencies.

`get_current_user` is the auth dependency every protected endpoint uses. It
validates the JWT, loads the user from the database, and ensures they are
still active.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User
from app.services import user_service

settings = get_settings()

# `auto_error=False` lets us return our own 401 with a clearer message.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)

SessionDep = Annotated[Session, Depends(get_session)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """Resolve the authenticated user from the bearer token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    subject = decode_access_token(token)
    if not subject:
        raise credentials_error

    try:
        from uuid import UUID

        user_id = UUID(subject)
    except ValueError as exc:
        raise credentials_error from exc

    user = user_service.get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
