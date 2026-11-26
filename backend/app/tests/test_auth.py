"""Authentication endpoint tests: Google sign-in, dev login, config, settings."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session

from app.api.v1.endpoints import auth as auth_endpoints
from app.core.config import Settings
from app.core.security import GoogleIdentity
from app.services import category_service, user_service

CLIENT_ID = "test-client.apps.googleusercontent.com"
ALICE = GoogleIdentity(sub="google-sub-alice", email="alice@gmail.com")


@pytest.fixture(name="google_on")
def google_on_fixture(use_settings: Callable[..., Settings]) -> Settings:
    return use_settings(
        google_auth_enabled=True,
        google_client_id=CLIENT_ID,
        allowed_emails="alice@gmail.com, Bob@Gmail.com",
    )


@pytest.fixture(name="fake_google")
def fake_google_fixture(monkeypatch: pytest.MonkeyPatch) -> Callable[[GoogleIdentity | None], None]:
    """Replace Google token verification with a canned result."""

    def _set(identity: GoogleIdentity | None) -> None:
        def _verify(token: str, client_id: str) -> GoogleIdentity | None:
            assert client_id == CLIENT_ID
            return identity

        monkeypatch.setattr(auth_endpoints, "verify_google_id_token", _verify)

    return _set


def _google_login(client: TestClient):
    return client.post("/api/v1/auth/google", json={"credential": "fake-id-token"})


# ---------- /auth/config ----------


def test_config_dev_mode(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/config")
    assert resp.status_code == 200
    assert resp.json() == {"google_enabled": False, "google_client_id": None}


def test_config_google_mode(client: TestClient, google_on: Settings) -> None:
    resp = client.get("/api/v1/auth/config")
    assert resp.json() == {"google_enabled": True, "google_client_id": CLIENT_ID}


# ---------- /auth/google ----------


def test_google_login_creates_user_with_default_categories(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    fake_google(ALICE)
    resp = _google_login(client)
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@gmail.com"

    user = user_service.get_user_by_google_sub(session, ALICE.sub)
    assert user is not None
    assert category_service.list_categories(session, user.id)


def test_google_login_reuses_existing_user(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    fake_google(ALICE)
    assert _google_login(client).status_code == 200
    assert _google_login(client).status_code == 200
    user = user_service.get_user_by_email(session, "alice@gmail.com")
    assert user is not None
    assert len(category_service.list_categories(session, user.id)) == len(
        category_service.DEFAULT_CATEGORIES
    )


def test_google_login_links_existing_user_by_email(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    existing = user_service.create_user_with_defaults(session, email="alice@gmail.com")
    fake_google(ALICE)
    assert _google_login(client).status_code == 200
    session.refresh(existing)
    assert existing.google_sub == ALICE.sub


def test_google_login_allow_list_is_case_insensitive(
    client: TestClient, google_on: Settings, fake_google
) -> None:
    fake_google(GoogleIdentity(sub="google-sub-bob", email="bob@gmail.com"))
    assert _google_login(client).status_code == 200


def test_google_login_rejects_email_not_allowed(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    fake_google(GoogleIdentity(sub="google-sub-eve", email="eve@gmail.com"))
    resp = _google_login(client)
    assert resp.status_code == 403
    assert user_service.get_user_by_email(session, "eve@gmail.com") is None


def test_google_login_rejects_email_linked_to_other_google_account(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    user_service.create_user_with_defaults(
        session, email="alice@gmail.com", google_sub="another-sub"
    )
    fake_google(ALICE)
    assert _google_login(client).status_code == 403


def test_google_login_rejects_inactive_user(
    client: TestClient, session: Session, google_on: Settings, fake_google
) -> None:
    user = user_service.create_user_with_defaults(
        session, email="alice@gmail.com", google_sub=ALICE.sub
    )
    user.is_active = False
    session.add(user)
    session.commit()
    fake_google(ALICE)
    assert _google_login(client).status_code == 403


def test_google_login_rejects_invalid_token(
    client: TestClient, google_on: Settings, fake_google
) -> None:
    fake_google(None)
    assert _google_login(client).status_code == 401


def test_google_login_unavailable_in_dev_mode(client: TestClient) -> None:
    assert _google_login(client).status_code == 404


def test_verify_google_id_token_requires_verified_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    claims = {"sub": "s", "email": "a@gmail.com", "email_verified": False}
    monkeypatch.setattr(
        security.google_id_token, "verify_oauth2_token", lambda token, req, aud: claims
    )
    assert security.verify_google_id_token("t", CLIENT_ID) is None

    claims["email_verified"] = True
    assert security.verify_google_id_token("t", CLIENT_ID) == GoogleIdentity(
        sub="s", email="a@gmail.com"
    )


def test_verify_google_id_token_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    def _raise(token, req, aud):
        raise ValueError("bad token")

    monkeypatch.setattr(security.google_id_token, "verify_oauth2_token", _raise)
    assert security.verify_google_id_token("t", CLIENT_ID) is None


# ---------- /auth/dev-login ----------


def test_dev_login_signs_in_as_dev_user(
    client: TestClient, use_settings: Callable[..., Settings]
) -> None:
    use_settings(dev_user_email="dev@example.com")
    resp = client.post("/api/v1/auth/dev-login")
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "dev@example.com"


def test_dev_login_disabled_when_google_enabled(client: TestClient, google_on: Settings) -> None:
    assert client.post("/api/v1/auth/dev-login").status_code == 404


def test_password_login_endpoints_removed(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login/json", json={"email": "a@example.com", "password": "x"})
    assert resp.status_code in (404, 405)


# ---------- /auth/me ----------


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_me_with_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["language"] == "en"
    assert "hashed_password" not in body
    assert "google_sub" not in body


# ---------- Settings safety ----------


def test_settings_refuse_dev_login_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            google_auth_enabled=False,
            secret_key="real-secret",
        )


def test_settings_require_client_id_when_google_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, google_auth_enabled=True, google_client_id=None)


def test_settings_require_secret_key_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            google_auth_enabled=True,
            google_client_id=CLIENT_ID,
        )


def test_settings_valid_production() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        google_auth_enabled=True,
        google_client_id=CLIENT_ID,
        secret_key="real-secret",
        allowed_emails=" A@x.com ,b@x.com,",
    )
    assert settings.allowed_emails_set == {"a@x.com", "b@x.com"}
