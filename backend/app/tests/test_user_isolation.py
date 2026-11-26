"""Multi-user isolation: one user must never see or change another user's data.

Alice owns data; Bob is a second, fully independent account. Every attempt by
Bob to read or modify Alice's resources must behave as if they don't exist.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.llm.tools.add_expense import AddExpenseInput, add_expense
from app.llm.tools.open_add_expense_form import OpenAddExpenseFormInput, open_add_expense_form
from app.llm.tools.search_expenses import search_expenses
from app.llm.tools.top_categories import TopCategoriesInput, top_categories
from app.models.user import User
from app.schemas.expense import ExpenseFilters

MONTH = "2026-03"


@pytest.fixture(name="alice_data")
def alice_data_fixture(
    client: TestClient, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> dict[str, Any]:
    alice, headers = make_user("alice@example.com")
    categories = client.get("/api/v1/categories", headers=headers).json()
    food_id = next(c["id"] for c in categories if c["slug"] == "food")
    expense = client.post(
        "/api/v1/expenses",
        json={
            "amount": "42.00",
            "expense_date": f"{MONTH}-10",
            "description": "Alice dinner",
            "category_id": food_id,
        },
        headers=headers,
    ).json()
    rule = client.post(
        "/api/v1/recurring-expenses",
        json={
            "amount": "500.00",
            "description": "Alice rent",
            "day_of_month": 1,
            "category_id": food_id,
        },
        headers=headers,
    ).json()
    return {
        "user": alice,
        "headers": headers,
        "food_id": food_id,
        "expense_id": expense["id"],
        "rule_id": rule["id"],
    }


@pytest.fixture(name="bob")
def bob_fixture(make_user: Callable[[str], tuple[User, dict[str, str]]]) -> tuple[User, dict]:
    return make_user("bob@example.com")


# ---------- Expenses ----------


def test_bob_cannot_read_update_or_delete_alice_expense(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob
    url = f"/api/v1/expenses/{alice_data['expense_id']}"

    assert client.get(url, headers=bob_headers).status_code == 404
    assert client.patch(url, json={"description": "hacked"}, headers=bob_headers).status_code == 404
    assert client.delete(url, headers=bob_headers).status_code == 404

    # Alice's expense is untouched.
    resp = client.get(url, headers=alice_data["headers"])
    assert resp.status_code == 200
    assert resp.json()["description"] == "Alice dinner"


def test_bob_lists_and_summaries_exclude_alice(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob

    listing = client.get("/api/v1/expenses", headers=bob_headers).json()
    assert listing["total"] == 0

    # Filtering by Alice's category id must not leak her expenses either.
    filtered = client.get(
        "/api/v1/expenses", params={"category_id": alice_data["food_id"]}, headers=bob_headers
    ).json()
    assert filtered["total"] == 0

    monthly = client.get(f"/api/v1/expenses/summary?month={MONTH}", headers=bob_headers).json()
    assert monthly["count"] == 0
    annual = client.get("/api/v1/expenses/annual-summary?year=2026", headers=bob_headers).json()
    assert annual["total"] == "0"

    # Sanity check: Alice does see her own data.
    alice_monthly = client.get(
        f"/api/v1/expenses/summary?month={MONTH}", headers=alice_data["headers"]
    ).json()
    assert alice_monthly["count"] == 1


def test_bob_cannot_use_alice_category(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob
    resp = client.post(
        "/api/v1/expenses",
        json={
            "amount": "1.00",
            "expense_date": f"{MONTH}-11",
            "description": "x",
            "category_id": alice_data["food_id"],
        },
        headers=bob_headers,
    )
    assert resp.status_code == 404

    bob_expense = client.post(
        "/api/v1/expenses",
        json={
            "amount": "1.00",
            "expense_date": f"{MONTH}-11",
            "description": "Bob coffee",
            "category_id": next(
                c["id"]
                for c in client.get("/api/v1/categories", headers=bob_headers).json()
                if c["slug"] == "food"
            ),
        },
        headers=bob_headers,
    ).json()
    resp = client.patch(
        f"/api/v1/expenses/{bob_expense['id']}",
        json={"category_id": alice_data["food_id"]},
        headers=bob_headers,
    )
    assert resp.status_code == 404


# ---------- Categories ----------


def test_bob_cannot_see_or_modify_alice_categories(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob
    bob_category_ids = {
        c["id"] for c in client.get("/api/v1/categories", headers=bob_headers).json()
    }
    assert alice_data["food_id"] not in bob_category_ids

    url = f"/api/v1/categories/{alice_data['food_id']}"
    assert client.patch(url, json={"icon": "x"}, headers=bob_headers).status_code == 404
    assert client.delete(url, headers=bob_headers).status_code == 404


# ---------- Recurring expenses ----------


def test_bob_cannot_access_alice_recurring_rule(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob
    url = f"/api/v1/recurring-expenses/{alice_data['rule_id']}"

    assert client.get("/api/v1/recurring-expenses", headers=bob_headers).json() == []
    assert client.get(url, headers=bob_headers).status_code == 404
    assert client.patch(url, json={"description": "hacked"}, headers=bob_headers).status_code == 404
    assert client.post(f"{url}/materialize-current-month", headers=bob_headers).status_code == 404
    assert client.delete(url, headers=bob_headers).status_code == 404
    assert client.get(url, headers=alice_data["headers"]).status_code == 200


def test_bob_cannot_create_rule_with_alice_category(
    client: TestClient, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    _, bob_headers = bob
    resp = client.post(
        "/api/v1/recurring-expenses",
        json={
            "amount": "10.00",
            "description": "x",
            "day_of_month": 5,
            "category_id": alice_data["food_id"],
        },
        headers=bob_headers,
    )
    assert resp.status_code == 404


# ---------- LLM tools (chat) ----------


def test_llm_tools_are_scoped_to_the_calling_user(
    session: Session, alice_data: dict[str, Any], bob: tuple[User, dict]
) -> None:
    bob_user, _ = bob

    found = search_expenses(session, bob_user.id, ExpenseFilters(description_contains="alice"))
    assert found["total"] == 0

    found = search_expenses(session, bob_user.id, ExpenseFilters(category_slug="food"))
    assert found["total"] == 0

    top = top_categories(session, bob_user.id, TopCategoriesInput())
    assert top["items"] == []

    with pytest.raises(HTTPException) as exc:
        add_expense(
            session,
            bob_user.id,
            AddExpenseInput(
                amount=5.0,
                expense_date=date(2026, 3, 12),
                description="x",
                category_id=alice_data["food_id"],
            ),
        )
    assert exc.value.status_code == 404

    # Bob's "food" slug resolves to Bob's own category, never Alice's.
    result = open_add_expense_form(
        session, bob_user.id, OpenAddExpenseFormInput(category_slug="food")
    )
    assert result["prefill"].get("category_id") != alice_data["food_id"]
