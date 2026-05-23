"""Authentication endpoints: login and self-info.

Single-user personal app: we deliberately don't expose a public /register
endpoint. The default user is created during the seed step. Add registration
later if you ever open this up to other users.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.security import create_access_token
from app.schemas.user import LoginRequest, Token, UserRead
from app.services import user_service
from typing import Annotated
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token, summary="Log in (OAuth2 form)")
def login_oauth2(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    """OAuth2-compatible login. The Swagger UI 'Authorize' button uses this."""
    user = user_service.authenticate(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.post("/login/json", response_model=Token, summary="Log in (JSON body)")
def login_json(payload: LoginRequest, session: SessionDep) -> Token:
    """JSON login endpoint, friendlier for SPA / mobile clients."""
    user = user_service.authenticate(session, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserRead, summary="Get the current user")
def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
