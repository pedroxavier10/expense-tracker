"""Unit tests for recurring_expense_service — especially date clamping and idempotency."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.models.recurring_expense import RecurringExpense
from app.services.recurring_expense_service import (
    materialize_all,
    materialize_for_rule,
    resolve_expense_date,
)

# --- resolve_expense_date ---


@pytest.mark.parametrize(
    "year,month,day,expected",
    [
        (2026, 2, 31, date(2026, 2, 28)),  # non-leap February
        (2024, 2, 31, date(2024, 2, 29)),  # leap February
        (2026, 4, 31, date(2026, 4, 30)),  # April has 30 days
        (2026, 1, 15, date(2026, 1, 15)),  # normal day, no clamping
        (2026, 3, 31, date(2026, 3, 31)),  # March has 31 days, no clamping
        (2026, 6, 30, date(2026, 6, 30)),  # last day of June
        (2026, 6, 31, date(2026, 6, 30)),  # June only has 30 days
    ],
)
def test_resolve_expense_date(year, month, day, expected):
    assert resolve_expense_date(year, month, day) == expected


# --- materialize_for_rule ---


def _make_rule(session: Session, user_id, category_id, day=10, is_active=True, end_date=None):
    rule = RecurringExpense(
        user_id=user_id,
        category_id=category_id,
        amount=Decimal("100.00"),
        description="Test rule",
        day_of_month=day,
        is_active=is_active,
        end_date=end_date,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def _get_food_category_id(session: Session, user_id):
    from sqlmodel import select
    from app.models.category import Category

    return (
        session.exec(select(Category).where(Category.user_id == user_id, Category.slug == "food"))
        .first()
        .id
    )


def _create_test_user(session: Session, email="rule_test@example.com"):
    from app.services import user_service

    return user_service.create_user_with_defaults(session, email=email)


def test_materialize_creates_expense(session: Session):
    user = _create_test_user(session)
    cat_id = _get_food_category_id(session, user.id)
    rule = _make_rule(session, user.id, cat_id, day=10)

    expense = materialize_for_rule(session, rule, 2026, 5)

    assert expense is not None
    assert expense.expense_date == date(2026, 5, 10)
    assert expense.is_recurring is True
    assert expense.recurring_expense_id == rule.id
    assert expense.user_id == user.id
    assert expense.amount == Decimal("100.00")


def test_materialize_clamps_day_to_last(session: Session):
    user = _create_test_user(session, "clamp@example.com")
    cat_id = _get_food_category_id(session, user.id)
    rule = _make_rule(session, user.id, cat_id, day=31)

    expense = materialize_for_rule(session, rule, 2026, 2)

    assert expense is not None
    assert expense.expense_date == date(2026, 2, 28)


def test_materialize_idempotent(session: Session):
    user = _create_test_user(session, "idempotent@example.com")
    cat_id = _get_food_category_id(session, user.id)
    rule = _make_rule(session, user.id, cat_id, day=5)

    first = materialize_for_rule(session, rule, 2026, 5)
    second = materialize_for_rule(session, rule, 2026, 5)

    assert first is not None
    assert second is None  # already exists, skipped


def test_materialize_inactive_rule_skipped(session: Session):
    user = _create_test_user(session, "inactive@example.com")
    cat_id = _get_food_category_id(session, user.id)
    rule = _make_rule(session, user.id, cat_id, is_active=False)

    result = materialize_for_rule(session, rule, 2026, 5)

    assert result is None


def test_materialize_past_end_date_skipped(session: Session):
    user = _create_test_user(session, "enddate@example.com")
    cat_id = _get_food_category_id(session, user.id)
    rule = _make_rule(session, user.id, cat_id, end_date=date(2026, 4, 30))

    result = materialize_for_rule(session, rule, 2026, 5)

    assert result is None


def test_materialize_end_date_same_month_allowed(session: Session):
    user = _create_test_user(session, "enddatesame@example.com")
    cat_id = _get_food_category_id(session, user.id)
    # end_date is within the target month, not before it
    rule = _make_rule(session, user.id, cat_id, day=10, end_date=date(2026, 5, 15))

    result = materialize_for_rule(session, rule, 2026, 5)

    assert result is not None


def test_materialize_all_creates_for_active_rules(session: Session):
    user = _create_test_user(session, "all_test@example.com")
    cat_id = _get_food_category_id(session, user.id)

    _make_rule(session, user.id, cat_id, day=5)
    _make_rule(session, user.id, cat_id, day=15)
    _make_rule(session, user.id, cat_id, is_active=False)  # inactive, should be skipped

    count = materialize_all(session, 2026, 5)

    assert count == 2


def test_materialize_all_idempotent(session: Session):
    user = _create_test_user(session, "all_idempotent@example.com")
    cat_id = _get_food_category_id(session, user.id)
    _make_rule(session, user.id, cat_id, day=10)

    first_run = materialize_all(session, 2026, 5)
    second_run = materialize_all(session, 2026, 5)

    assert first_run == 1
    assert second_run == 0
