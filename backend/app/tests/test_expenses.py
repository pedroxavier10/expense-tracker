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


# ---------- Summary endpoints ----------


def test_monthly_summary_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/expenses/summary?month=2020-01", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == "2020-01"
    assert body["total"] == "0"
    assert body["count"] == 0
    assert body["by_category"] == []


def test_monthly_summary_aggregates_correctly(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    food_id = _get_category_id(client, auth_headers, "food")
    transport_id = _get_category_id(client, auth_headers, "transport")

    for amount, cat_id in [("10.00", food_id), ("5.50", food_id), ("20.00", transport_id)]:
        client.post(
            "/api/v1/expenses",
            json={
                "amount": amount,
                "expense_date": "2025-03-15",
                "description": "x",
                "category_id": cat_id,
            },
            headers=auth_headers,
        )

    resp = client.get("/api/v1/expenses/summary?month=2025-03", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == "35.50"
    assert body["count"] == 3
    slugs = {c["slug"]: c for c in body["by_category"]}
    assert slugs["food"]["total"] == "15.50"
    assert slugs["food"]["count"] == 2
    assert slugs["transport"]["total"] == "20.00"


def test_monthly_summary_missing_month_param(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/expenses/summary", headers=auth_headers)
    assert resp.status_code == 422


def test_annual_summary_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/expenses/annual-summary?year=2019", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2019
    assert body["total"] == "0"
    assert len(body["by_month"]) == 12
    assert all(m["total"] == "0" for m in body["by_month"])
    assert body["by_category"] == []


def test_annual_summary_aggregates_correctly(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    food_id = _get_category_id(client, auth_headers, "food")

    client.post(
        "/api/v1/expenses",
        json={
            "amount": "100.00",
            "expense_date": "2024-01-10",
            "description": "jan",
            "category_id": food_id,
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/expenses",
        json={
            "amount": "200.00",
            "expense_date": "2024-06-15",
            "description": "jun",
            "category_id": food_id,
        },
        headers=auth_headers,
    )

    resp = client.get("/api/v1/expenses/annual-summary?year=2024", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == "300.00"
    assert len(body["by_month"]) == 12
    months = {m["month"]: m["total"] for m in body["by_month"]}
    assert months["2024-01"] == "100.00"
    assert months["2024-06"] == "200.00"
    assert months["2024-03"] == "0"
    assert body["by_category"][0]["slug"] == "food"
    assert body["by_category"][0]["total"] == "300.00"
