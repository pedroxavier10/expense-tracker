"""Recurring expense endpoint tests: CRUD + materialize."""

from fastapi.testclient import TestClient


def _get_category_id(client: TestClient, headers: dict[str, str], slug: str) -> str:
    response = client.get("/api/v1/categories", headers=headers)
    assert response.status_code == 200
    for cat in response.json():
        if cat["slug"] == slug:
            return cat["id"]
    raise AssertionError(f"Category {slug} not found")


def _create_rule(client, headers, category_id, day=10, description="Rent", amount="500.00"):
    return client.post(
        "/api/v1/recurring-expenses",
        json={
            "amount": amount,
            "description": description,
            "day_of_month": day,
            "category_id": category_id,
        },
        headers=headers,
    )


def test_create_recurring_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "other")
    resp = _create_rule(client, auth_headers, cat_id, day=15, description="Internet")
    assert resp.status_code == 201
    body = resp.json()
    assert body["description"] == "Internet"
    assert body["day_of_month"] == 15
    assert body["is_active"] is True
    assert body["category"]["slug"] == "other"


def test_list_recurring_expenses(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "food")
    _create_rule(client, auth_headers, cat_id)
    _create_rule(client, auth_headers, cat_id, day=20, description="Gym")

    resp = client.get("/api/v1/recurring-expenses", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_recurring_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "health")
    created = _create_rule(client, auth_headers, cat_id, description="Gym").json()

    resp = client.get(f"/api/v1/recurring-expenses/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_nonexistent_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/recurring-expenses/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_update_recurring_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "other")
    created = _create_rule(client, auth_headers, cat_id).json()

    resp = client.patch(
        f"/api/v1/recurring-expenses/{created['id']}",
        json={"is_active": False, "day_of_month": 28},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["day_of_month"] == 28


def test_delete_recurring_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "other")
    created = _create_rule(client, auth_headers, cat_id).json()

    resp = client.delete(f"/api/v1/recurring-expenses/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/api/v1/recurring-expenses/{created['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_delete_preserves_is_recurring_flag_on_expenses(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    cat_id = _get_category_id(client, auth_headers, "food")
    rule = _create_rule(client, auth_headers, cat_id, day=1).json()

    # Materialize to create an expense linked to this rule
    mat_resp = client.post(
        f"/api/v1/recurring-expenses/{rule['id']}/materialize-current-month",
        headers=auth_headers,
    )
    assert mat_resp.status_code == 201
    expense_id = mat_resp.json()["id"]

    # Delete the rule
    client.delete(f"/api/v1/recurring-expenses/{rule['id']}", headers=auth_headers)

    # The expense should still have is_recurring=True but recurring_expense_id=None
    expense_resp = client.get(f"/api/v1/expenses/{expense_id}", headers=auth_headers)
    assert expense_resp.status_code == 200
    expense = expense_resp.json()
    assert expense["is_recurring"] is True
    assert expense["recurring_expense_id"] is None


def test_invalid_day_of_month_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "other")
    resp = client.post(
        "/api/v1/recurring-expenses",
        json={"amount": "10.00", "description": "x", "day_of_month": 32, "category_id": cat_id},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_user_isolation(
    client: TestClient, auth_headers: dict[str, str], session
) -> None:
    from app.core.security import create_access_token
    from app.services import user_service

    other_user = user_service.create_user(session, email="other2@example.com")
    other_token = create_access_token(subject=str(other_user.id))
    other_headers = {"Authorization": f"Bearer {other_token}"}

    cat_id = _get_category_id(client, auth_headers, "food")
    rule = _create_rule(client, auth_headers, cat_id).json()

    # Other user should not see or modify the rule
    resp = client.get(f"/api/v1/recurring-expenses/{rule['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_materialize_current_month(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "food")
    rule = _create_rule(client, auth_headers, cat_id, day=1).json()

    resp = client.post(
        f"/api/v1/recurring-expenses/{rule['id']}/materialize-current-month",
        headers=auth_headers,
    )
    assert resp.status_code == 201
    expense = resp.json()
    assert expense["is_recurring"] is True
    assert expense["recurring_expense_id"] == rule["id"]
    assert expense["category"]["slug"] == "food"


def test_materialize_twice_returns_409(client: TestClient, auth_headers: dict[str, str]) -> None:
    cat_id = _get_category_id(client, auth_headers, "transport")
    rule = _create_rule(client, auth_headers, cat_id).json()

    client.post(
        f"/api/v1/recurring-expenses/{rule['id']}/materialize-current-month",
        headers=auth_headers,
    )
    second = client.post(
        f"/api/v1/recurring-expenses/{rule['id']}/materialize-current-month",
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_unauthenticated_access_fails(client: TestClient) -> None:
    resp = client.get("/api/v1/recurring-expenses")
    assert resp.status_code == 401
