"""Recurring-expense suggestions: detection, dismissal, acceptance and triggers."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.llm.tools.add_expense import AddExpenseInput, add_expense
from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring_expense import RecurringExpense
from app.models.recurring_suggestion_dismissal import RecurringSuggestionDismissal
from app.models.user import User
from app.schemas.recurring_expense import RecurringExpenseCreate
from app.services import category_service, recurring_expense_service
from app.services import recurring_suggestion_service as service
from app.services.chat_service import _split_followup_action

MakeUser = Callable[[str], tuple[User, dict[str, str]]]

TODAY = date(2026, 11, 26)


def _months_ago(n: int, day: int = 5, today: date = TODAY) -> date:
    index = today.year * 12 + today.month - 1 - n
    return date(index // 12, index % 12 + 1, day)


def _category(session: Session, user: User, slug: str = "leisure") -> Category:
    category = category_service.get_category_by_slug(session, user.id, slug)
    assert category
    return category


def _expense(
    session: Session,
    user: User,
    day: date,
    amount: str = "35.00",
    description: str = "Ginásio",
    category: Category | None = None,
    created_at: datetime | None = None,
) -> Expense:
    expense = Expense(
        user_id=user.id,
        category_id=(category or _category(session, user)).id,
        amount=Decimal(amount),
        expense_date=day,
        description=description,
    )
    if created_at is not None:
        expense.created_at = created_at
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def _key(session: Session, user: User, description: str = "Ginásio") -> str:
    key = service.pattern_key(_category(session, user).id, description)
    assert key
    return key


def _monthly(session: Session, user: User, months: int, **kwargs: object) -> list[Expense]:
    """One expense per month, oldest first, ending in the current month."""
    return [
        _expense(session, user, _months_ago(n), **kwargs)  # type: ignore[arg-type]
        for n in range(months - 1, -1, -1)
    ]


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------


def test_three_months_is_a_suggestion(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("three@example.com")
    _expense(session, user, _months_ago(2, day=3))
    _expense(session, user, _months_ago(1, day=6))
    _expense(session, user, _months_ago(0, day=5), description="ginásio mensalidade de")

    suggestion = service.find_by_key(session, user.id, _key(session, user), TODAY)

    # "ginásio mensalidade" has a different key, so only 2 months match.
    assert suggestion is None

    _expense(session, user, _months_ago(0, day=5), amount="35.50")
    suggestion = service.find_by_key(session, user.id, _key(session, user), TODAY)
    assert suggestion is not None
    assert suggestion.months == 3
    assert suggestion.amount == Decimal("35.50")  # most recent occurrence
    assert suggestion.day_of_month == 5  # median of 3, 6, 5
    assert suggestion.category.slug == "leisure"


def test_two_months_is_not_enough(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("two@example.com")
    _monthly(session, user, 2)
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is None


def test_daily_expense_is_not_suggested(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("coffee@example.com")
    for n in range(3):
        for day in (2, 9, 16, 23):
            _expense(session, user, _months_ago(n, day=day), amount="1.20", description="Café")
    assert service.find_by_key(session, user.id, _key(session, user, "Café"), TODAY) is None


def test_one_extra_occurrence_is_tolerated(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("extra@example.com")
    _monthly(session, user, 3)
    _expense(session, user, _months_ago(1, day=20))  # registered twice that month
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is not None


def test_different_amount_breaks_the_pattern(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("amount@example.com")
    _expense(session, user, _months_ago(2))
    _expense(session, user, _months_ago(1))
    _expense(session, user, _months_ago(0), amount="50.00")
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is None


def test_stopped_pattern_is_not_suggested(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("stopped@example.com")
    for n in (5, 4, 3):
        _expense(session, user, _months_ago(n))
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is None


def test_previous_month_still_counts(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("previous@example.com")
    for n in (3, 2, 1):
        _expense(session, user, _months_ago(n))
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is not None


def test_existing_active_rule_suppresses_suggestion(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("rule@example.com")
    _monthly(session, user, 3)
    recurring_expense_service.create_recurring_expense(
        session,
        user.id,
        RecurringExpenseCreate(
            amount=Decimal("35.00"),
            description="ginasio",
            day_of_month=5,
            category_id=_category(session, user).id,
        ),
    )
    assert service.find_by_key(session, user.id, _key(session, user), TODAY) is None


def test_invalid_or_foreign_key_returns_none(session: Session, make_user: MakeUser) -> None:
    owner, _ = make_user("owner@example.com")
    other, _ = make_user("other@example.com")
    _monthly(session, owner, 3)
    assert service.find_by_key(session, other.id, _key(session, owner), TODAY) is None
    assert service.find_by_key(session, owner.id, "not-a-key", TODAY) is None


# ---------------------------------------------------------------------------
# Trigger on a just-registered expense
# ---------------------------------------------------------------------------


def test_find_for_expense_only_when_it_is_an_occurrence(
    session: Session, make_user: MakeUser
) -> None:
    user, _ = make_user("trigger@example.com")
    expenses = _monthly(session, user, 3)
    unrelated = _expense(session, user, TODAY, description="Cinema")

    assert service.find_for_expense(session, user.id, expenses[-1], TODAY) is not None
    assert service.find_for_expense(session, user.id, unrelated, TODAY) is None


# ---------------------------------------------------------------------------
# Dismissal ("No") resets the count
# ---------------------------------------------------------------------------


def test_dismissal_resets_the_count(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("dismiss@example.com")
    key = _key(session, user)
    old = datetime.now(UTC) - timedelta(days=400)
    for n in (2, 1, 0):
        _expense(session, user, _months_ago(n), created_at=old)
    assert service.find_by_key(session, user.id, key, TODAY) is not None

    service.dismiss(session, user.id, key)
    assert service.find_by_key(session, user.id, key, TODAY) is None

    # New registrations after the "No" count again from zero.
    later = datetime.now(UTC) + timedelta(minutes=1)
    for n in (2, 1):
        _expense(session, user, _months_ago(n, day=6), created_at=later)
    assert service.find_by_key(session, user.id, key, TODAY) is None
    _expense(session, user, _months_ago(0, day=6), created_at=later)
    assert service.find_by_key(session, user.id, key, TODAY) is not None


def test_dismissing_twice_keeps_one_row(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("twice@example.com")
    key = _key(session, user)
    service.dismiss(session, user.id, key)
    service.dismiss(session, user.id, key)
    rows = session.exec(
        select(RecurringSuggestionDismissal).where(RecurringSuggestionDismissal.user_id == user.id)
    ).all()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


def _rule_in(session: Session, user: User) -> RecurringExpenseCreate:
    return RecurringExpenseCreate(
        amount=Decimal("35.00"),
        description="Ginásio",
        day_of_month=5,
        category_id=_category(session, user).id,
    )


def test_accept_creates_rule_and_links_expenses(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("accept@example.com")
    key = _key(session, user)
    expenses = _monthly(session, user, 3)
    service.dismiss(session, user.id, "other:key")  # unrelated dismissal untouched

    result = service.accept(session, user.id, key, _rule_in(session, user), TODAY)

    assert result is not None
    assert result.linked_expenses == 3
    assert result.current_month_covered is True
    for expense in expenses:
        session.refresh(expense)
        assert expense.recurring_expense_id == result.rule.id
        assert expense.is_recurring is True
    # The current month is already registered: materializing must not duplicate it.
    assert (
        recurring_expense_service.materialize_for_rule(
            session, result.rule, TODAY.year, TODAY.month
        )
        is None
    )
    assert service.find_by_key(session, user.id, key, TODAY) is None


def test_accept_links_occurrences_from_before_a_dismissal(
    session: Session, make_user: MakeUser
) -> None:
    user, _ = make_user("relink@example.com")
    key = _key(session, user)
    old = datetime.now(UTC) - timedelta(days=400)
    for n in (5, 4):
        _expense(session, user, _months_ago(n), created_at=old)
    service.dismiss(session, user.id, key)
    later = datetime.now(UTC) + timedelta(minutes=1)
    for n in (2, 1):
        _expense(session, user, _months_ago(n), created_at=later)
    _expense(session, user, _months_ago(0), created_at=later)

    result = service.accept(session, user.id, key, _rule_in(session, user), TODAY)

    assert result is not None
    assert result.linked_expenses == 5
    assert service._get_dismissal(session, user.id, key) is None


def test_accept_previous_month_pattern_is_not_covered(
    session: Session, make_user: MakeUser
) -> None:
    user, _ = make_user("notcovered@example.com")
    for n in (3, 2, 1):
        _expense(session, user, _months_ago(n))

    result = service.accept(session, user.id, _key(session, user), _rule_in(session, user), TODAY)

    assert result is not None
    assert result.current_month_covered is False


def test_accept_when_no_longer_valid_returns_none(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("invalid@example.com")
    _monthly(session, user, 2)
    assert (
        service.accept(session, user.id, _key(session, user), _rule_in(session, user), TODAY)
        is None
    )
    assert session.exec(select(RecurringExpense)).all() == []


# ---------------------------------------------------------------------------
# REST API (uses the real current date)
# ---------------------------------------------------------------------------


def _post_expense(
    client: TestClient, headers: dict[str, str], category: Category, day: date
) -> dict:
    response = client.post(
        "/api/v1/expenses",
        json={
            "amount": "35.00",
            "expense_date": day.isoformat(),
            "description": "Ginásio",
            "category_id": str(category.id),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_post_expense_returns_suggestion_on_third_month(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("api@example.com")
    category = _category(session, user)
    today = datetime.now(UTC).date()

    first = _post_expense(client, headers, category, _months_ago(2, today=today))
    second = _post_expense(client, headers, category, _months_ago(1, today=today))
    third = _post_expense(client, headers, category, _months_ago(0, today=today))

    assert first["recurring_suggestion"] is None
    assert second["recurring_suggestion"] is None
    suggestion = third["recurring_suggestion"]
    assert suggestion["months"] == 3
    assert suggestion["amount"] == "35.00"
    assert suggestion["category"]["id"] == str(category.id)
    assert len(suggestion["expense_ids"]) == 3

    accepted = client.post(
        "/api/v1/recurring-suggestions/accept",
        json={
            "pattern_key": suggestion["pattern_key"],
            "rule": {
                "amount": "35.00",
                "description": "Ginásio",
                "day_of_month": suggestion["day_of_month"],
                "category_id": str(category.id),
            },
        },
        headers=headers,
    )
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert body["linked_expenses"] == 3
    assert body["current_month_covered"] is True
    assert body["rule"]["description"] == "Ginásio"

    again = client.post(
        "/api/v1/recurring-suggestions/accept",
        json={
            "pattern_key": suggestion["pattern_key"],
            "rule": {
                "amount": "35.00",
                "description": "Ginásio",
                "day_of_month": 5,
                "category_id": str(category.id),
            },
        },
        headers=headers,
    )
    assert again.status_code == 409


def test_dismiss_endpoint_stops_suggestion(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("apidismiss@example.com")
    category = _category(session, user)
    today = datetime.now(UTC).date()
    for n in (2, 1):
        _post_expense(client, headers, category, _months_ago(n, today=today))
    suggestion = _post_expense(client, headers, category, _months_ago(0, today=today))[
        "recurring_suggestion"
    ]

    response = client.post(
        "/api/v1/recurring-suggestions/dismiss",
        json={"pattern_key": suggestion["pattern_key"]},
        headers=headers,
    )

    assert response.status_code == 204
    fourth = _post_expense(client, headers, category, _months_ago(0, day=20, today=today))
    assert fourth["recurring_suggestion"] is None


def test_accept_rejects_foreign_category(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("foreign@example.com")
    other, _ = make_user("someone@example.com")
    response = client.post(
        "/api/v1/recurring-suggestions/accept",
        json={
            "pattern_key": _key(session, user),
            "rule": {
                "amount": "35.00",
                "description": "Ginásio",
                "day_of_month": 5,
                "category_id": str(_category(session, other).id),
            },
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_endpoints_require_auth(client: TestClient) -> None:
    assert (
        client.post("/api/v1/recurring-suggestions/dismiss", json={"pattern_key": "x:y"})
    ).status_code == 401


# ---------------------------------------------------------------------------
# Chat tool
# ---------------------------------------------------------------------------


def test_add_expense_tool_emits_followup_action(session: Session, make_user: MakeUser) -> None:
    user, _ = make_user("tool@example.com")
    category = _category(session, user)
    today = datetime.now(UTC).date()
    for n in (2, 1):
        _expense(session, user, _months_ago(n, today=today))

    result = add_expense(
        session,
        user.id,
        AddExpenseInput(
            amount=35.0,
            expense_date=_months_ago(0, today=today),
            description="Ginásio",
            category_id=category.id,
        ),
    )
    for_model, client_action = _split_followup_action(result)

    assert client_action is not None
    assert client_action["action"] == "suggest_recurring_expense"
    assert client_action["payload"]["recurring_suggestion"]["months"] == 3
    assert "followup_action" not in for_model
    assert for_model["recurring_suggestion_shown"] is True


def test_add_expense_tool_without_pattern_has_no_followup(
    session: Session, make_user: MakeUser
) -> None:
    user, _ = make_user("tool2@example.com")
    result = add_expense(
        session,
        user.id,
        AddExpenseInput(
            amount=12.5,
            expense_date=datetime.now(UTC).date(),
            description="Almoço",
            category_id=_category(session, user, "food").id,
        ),
    )
    assert _split_followup_action(result) == (result, None)
