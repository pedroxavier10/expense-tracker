"""Category endpoint tests: per-user CRUD, slug generation, delete vs archive."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.services import slug_service, user_service


@pytest.fixture(autouse=True)
def _force_local_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the network LLM call so slugs come from the deterministic local
    fallback (accent-stripping slugify). Keeps tests offline and predictable."""

    async def _no_llm(_name: str, _existing: set[str]) -> str:
        return ""

    monkeypatch.setattr(slug_service, "_llm_suggest_slug", _no_llm)


def _slugs(client: TestClient, headers: dict[str, str], include_inactive: bool = False) -> set[str]:
    resp = client.get(
        "/api/v1/categories",
        params={"include_inactive": include_inactive},
        headers=headers,
    )
    assert resp.status_code == 200
    return {c["slug"] for c in resp.json()}


def _second_user_headers(session: Session) -> dict[str, str]:
    user = user_service.create_user_with_defaults(
        session, email="other@example.com"
    )
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def test_create_category_generates_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/categories", json={"name": "Café", "icon": "☕"}, headers=auth_headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "cafe"
    assert body["name"] == "Café"
    assert body["icon"] == "☕"
    assert body["is_active"] is True
    assert "cafe" in _slugs(client, auth_headers)


def test_create_category_slug_collision_is_suffixed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # "food" already exists as a default category for the user.
    resp = client.post("/api/v1/categories", json={"name": "Food"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["slug"] == "food-2"


def test_rename_regenerates_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/categories", json={"name": "Refeição"}, headers=auth_headers
    ).json()
    assert created["slug"] == "refeicao"

    updated = client.patch(
        f"/api/v1/categories/{created['id']}",
        json={"name": "Escola"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == "escola"


def test_update_icon_only_keeps_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/categories", json={"name": "Gym", "icon": "🏃"}, headers=auth_headers
    ).json()
    assert created["slug"] == "gym"

    updated = client.patch(
        f"/api/v1/categories/{created['id']}",
        json={"icon": "🏋️"},
        headers=auth_headers,
    ).json()
    assert updated["slug"] == "gym"
    assert updated["icon"] == "🏋️"


def test_delete_unused_category_hard_deletes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/categories", json={"name": "Temp"}, headers=auth_headers
    ).json()

    resp = client.delete(f"/api/v1/categories/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["action"] == "deleted"
    # Gone entirely, even when including inactive.
    assert "temp" not in _slugs(client, auth_headers, include_inactive=True)


def test_delete_used_category_archives_then_restore(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/categories", json={"name": "Subscriptions"}, headers=auth_headers
    ).json()
    # Use the category on an expense.
    exp = client.post(
        "/api/v1/expenses",
        json={
            "amount": "9.99",
            "expense_date": "2026-05-01",
            "description": "Music",
            "category_id": created["id"],
        },
        headers=auth_headers,
    )
    assert exp.status_code == 201

    resp = client.delete(f"/api/v1/categories/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "archived"
    assert body["category"]["is_active"] is False

    # Hidden from the default list, visible when including inactive.
    assert created["slug"] not in _slugs(client, auth_headers)
    assert created["slug"] in _slugs(client, auth_headers, include_inactive=True)

    # Restore it.
    restored = client.patch(
        f"/api/v1/categories/{created['id']}",
        json={"is_active": True},
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
    assert created["slug"] in _slugs(client, auth_headers)


def test_categories_are_isolated_per_user(
    client: TestClient, auth_headers: dict[str, str], session: Session
) -> None:
    created = client.post(
        "/api/v1/categories", json={"name": "Private"}, headers=auth_headers
    ).json()

    other = _second_user_headers(session)
    # Other user does not see it.
    assert created["slug"] not in _slugs(client, other, include_inactive=True)
    # Other user cannot update or delete it.
    assert client.patch(
        f"/api/v1/categories/{created['id']}", json={"name": "Hack"}, headers=other
    ).status_code == 404
    assert client.delete(
        f"/api/v1/categories/{created['id']}", headers=other
    ).status_code == 404
