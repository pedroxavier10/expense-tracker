"""Authentication endpoints: Google sign-in, dev login and self-info.

Production only accepts Google sign-in, restricted to `ALLOWED_EMAILS`. When
`GOOGLE_AUTH_ENABLED=false` (development only — refused at startup in
production) a passwordless dev login signs in as `DEV_USER_EMAIL`.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.core.security import create_access_token, verify_google_id_token
from app.schemas.user import AuthConfig, GoogleLoginRequest, Token, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig, summary="Public auth configuration")
def read_auth_config(settings: SettingsDep) -> AuthConfig:
    """Tell the client which login flow to show. The client id is not a secret."""
    return AuthConfig(
        google_enabled=settings.google_auth_enabled,
        google_client_id=settings.google_client_id if settings.google_auth_enabled else None,
    )


@router.post("/google", response_model=Token, summary="Sign in with a Google ID token")
def login_google(payload: GoogleLoginRequest, session: SessionDep, settings: SettingsDep) -> Token:
    if not settings.google_auth_enabled or not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    identity = verify_google_id_token(payload.credential, settings.google_client_id)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential"
        )

    user = user_service.login_with_google(session, identity, settings.allowed_emails_set)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is not allowed"
        )
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.post("/dev-login", response_model=Token, summary="Dev-only passwordless login")
def login_dev(session: SessionDep, settings: SettingsDep) -> Token:
    """Only available when Google sign-in is disabled (never in production)."""
    if settings.google_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    user = user_service.get_or_create_dev_user(session, settings.dev_user_email)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserRead, summary="Get the current user")
def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead, summary="Update current user preferences")
def update_current_user(
    payload: UserUpdate, session: SessionDep, current_user: CurrentUser
) -> UserRead:
    updated = user_service.update_user(session, current_user, payload)
    return UserRead.model_validate(updated)
