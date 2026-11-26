"""Shared FastAPI dependencies.

`get_current_user` is the auth dependency every protected endpoint uses. It
validates the app JWT, loads the user from the database, and ensures they are
still active. Every service call then scopes data by `current_user.id`, which
is what keeps one user's data invisible to another.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User
from app.services import user_service

# `auto_error=False` lets us return our own 401 with a clearer message.
bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(session: SessionDep, credentials: CredentialsDep) -> User:
    """Resolve the authenticated user from the bearer token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error

    subject = decode_access_token(credentials.credentials)
    if not subject:
        raise credentials_error

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise credentials_error from exc

    user = user_service.get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
