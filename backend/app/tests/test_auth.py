"""Authentication endpoint tests."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.services import user_service


def test_login_json_success(client: TestClient, session: Session) -> None:
    user_service.create_user(session, email="alice@example.com", password="secret123")
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_json_wrong_password(client: TestClient, session: Session) -> None:
    user_service.create_user(session, email="bob@example.com", password="secret123")
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
