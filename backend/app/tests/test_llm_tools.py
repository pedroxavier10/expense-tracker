"""Direct tests for the new LLM tool handlers.

These call the handlers as Python functions — no HTTP, no LLM. That's the
whole point of the tool design: every tool is unit-testable in isolation.
"""

from decimal import Decimal
from uuid import uuid4

from sqlmodel import Session

from app.llm.tools.list_categories import ListCategoriesInput, list_categories
from app.llm.tools.monthly_summary import MonthlySummaryInput, monthly_summary
from app.llm.tools.open_add_expense_form import (
    OpenAddExpenseFormInput,
    open_add_expense_form,
)
from app.llm.tools.top_categories import TopCategoriesInput, top_categories
from app.models.expense import Expense
from app.services import category_service, user_service


def _make_user_and_expenses(session: Session) -> tuple:
    user = user_service.create_user(session, email="llm@example.com", password="pw12345678")
    food = category_service.get_category_by_slug(session, "food")
    transport = category_service.get_category_by_slug(session, "transport")
    assert food and transport

    rows = [
        ("2026-04-10", "10.00", food.id, "lunch april"),
        ("2026-05-01", "12.50", food.id, "lunch may"),
        ("2026-05-15", "20.00", food.id, "dinner"),
        ("2026-05-20", "5.00", transport.id, "bus"),
    ]
    for d, amt, cid, desc in rows:
        e = Expense(
            user_id=user.id,
            category_id=cid,
            amount=Decimal(amt),
            expense_date=__import__("datetime").date.fromisoformat(d),
            description=desc,
        )
        session.add(e)
    session.commit()
    return user, food, transport


def test_list_categories(session: Session) -> None:
    result = list_categories(session, uuid4(), ListCategoriesInput())
    slugs = {c["slug"] for c in result["categories"]}
    assert {"food", "transport", "health", "other"} <= slugs
    for c in result["categories"]:
        assert {"id", "slug", "name", "icon"} <= set(c.keys())


def test_monthly_summary_groups_by_category(session: Session) -> None:
    user, food, transport = _make_user_and_expenses(session)

    result = monthly_summary(session, user.id, MonthlySummaryInput(month="2026-05"))
    assert result["month"] == "2026-05"
    assert Decimal(result["total"]) == Decimal("37.50")
    assert result["count"] == 3

    by_slug = {c["slug"]: c for c in result["by_category"]}
    assert Decimal(by_slug["food"]["total"]) == Decimal("32.50")
    assert by_slug["food"]["count"] == 2
    assert Decimal(by_slug["transport"]["total"]) == Decimal("5.00")


def test_monthly_summary_empty_month(session: Session) -> None:
    user, *_ = _make_user_and_expenses(session)
    result = monthly_summary(session, user.id, MonthlySummaryInput(month="2026-03"))
    assert Decimal(result["total"]) == Decimal("0")
    assert result["count"] == 0
    assert result["by_category"] == []


def test_top_categories_orders_by_total_desc(session: Session) -> None:
    user, *_ = _make_user_and_expenses(session)
    from datetime import date

    result = top_categories(
        session,
        user.id,
        TopCategoriesInput(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31), limit=5),
    )
    items = result["items"]
    assert len(items) == 2
    assert items[0]["slug"] == "food"
    assert Decimal(items[0]["total"]) == Decimal("42.50")
    assert items[1]["slug"] == "transport"


def test_top_categories_respects_limit(session: Session) -> None:
    user, *_ = _make_user_and_expenses(session)
    result = top_categories(session, user.id, TopCategoriesInput(limit=1))
    assert len(result["items"]) == 1
    assert result["items"][0]["slug"] == "food"


def test_open_add_expense_form_resolves_slug(session: Session) -> None:
    user = user_service.create_user(session, email="form@example.com", password="pw12345678")
    food = category_service.get_category_by_slug(session, "food")
    assert food

    result = open_add_expense_form(
        session,
        user.id,
        OpenAddExpenseFormInput(
            amount=Decimal("23.00"),
            description="jantar continente",
            category_slug="food",
        ),
    )
    assert result["action"] == "open_add_expense_form"
    prefill = result["prefill"]
    assert prefill["amount"] == "23.00"
    assert prefill["description"] == "jantar continente"
    assert prefill["category_id"] == str(food.id)
    assert "expense_date" not in prefill  # not provided -> omitted


def test_open_add_expense_form_unknown_slug_is_dropped(session: Session) -> None:
    user = user_service.create_user(session, email="form2@example.com", password="pw12345678")
    result = open_add_expense_form(
        session,
        user.id,
        OpenAddExpenseFormInput(amount=Decimal("5.00"), category_slug="not-a-real-slug"),
    )
    assert result["action"] == "open_add_expense_form"
    assert "category_id" not in result["prefill"]
    assert result["prefill"]["amount"] == "5.00"
