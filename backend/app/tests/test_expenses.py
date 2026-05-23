"""Expense endpoint tests: CRUD + filters."""

from fastapi.testclient import TestClient


def _get_category_id(client: TestClient, headers: dict[str, str], slug: str) -> str:
    response = client.get("/api/v1/categories", headers=headers)
    assert response.status_code == 200
    for cat in response.json():
        if cat["slug"] == slug:
            return cat["id"]
    raise AssertionError(f"Category {slug} not found in seed")


def test_list_categories(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/categories", headers=auth_headers)
    assert response.status_code == 200
    slugs = {c["slug"] for c in response.json()}
    assert {"food", "transport", "health", "other"} <= slugs


def test_create_and_list_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    food_id = _get_category_id(client, auth_headers, "food")
    payload = {
        "amount": "12.50",
        "expense_date": "2026-05-01",
        "description": "Lunch",
        "category_id": food_id,
    }
    create_resp = client.post("/api/v1/expenses", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["description"] == "Lunch"
    assert created["category"]["slug"] == "food"

    list_resp = client.get("/api/v1/expenses", headers=auth_headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == created["id"]


def test_update_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    food_id = _get_category_id(client, auth_headers, "food")
    created = client.post(
        "/api/v1/expenses",
        json={
            "amount": "5.00",
            "expense_date": "2026-05-01",
            "description": "Coffee",
            "category_id": food_id,
        },
        headers=auth_headers,
    ).json()

    resp = client.patch(
        f"/api/v1/expenses/{created['id']}",
        json={"amount": "7.50"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == "7.50"


def test_delete_expense(client: TestClient, auth_headers: dict[str, str]) -> None:
    other_id = _get_category_id(client, auth_headers, "other")
    created = client.post(
        "/api/v1/expenses",
        json={
            "amount": "1.00",
            "expense_date": "2026-05-01",
            "description": "x",
            "category_id": other_id,
        },
        headers=auth_headers,
    ).json()

    resp = client.delete(f"/api/v1/expenses/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/api/v1/expenses/{created['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_filter_by_month(client: TestClient, auth_headers: dict[str, str]) -> None:
    food_id = _get_category_id(client, auth_headers, "food")
    for d in ["2026-04-15", "2026-05-01", "2026-05-20", "2026-06-02"]:
        client.post(
            "/api/v1/expenses",
            json={
                "amount": "1.00",
                "expense_date": d,
                "description": d,
                "category_id": food_id,
            },
            headers=auth_headers,
        )

    resp = client.get("/api/v1/expenses?month=2026-05", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2


def test_filter_by_date_range_and_category(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    food_id = _get_category_id(client, auth_headers, "food")
    transport_id = _get_category_id(client, auth_headers, "transport")

    client.post(
        "/api/v1/expenses",
        json={
            "amount": "10",
            "expense_date": "2026-05-10",
            "description": "lunch",
            "category_id": food_id,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/expenses",
        json={
            "amount": "20",
            "expense_date": "2026-05-10",
            "description": "bus",
            "category_id": transport_id,
        },
        headers=auth_headers,
    )

    resp = client.get(
        f"/api/v1/expenses?date_from=2026-05-01&date_to=2026-05-31&category_id={transport_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["description"] == "bus"


def test_unauthenticated_expense_list_fails(client: TestClient) -> None:
    resp = client.get("/api/v1/expenses")
    assert resp.status_code == 401
