"""Category learning: corrections become hints, hints/history drive suggestions."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.llm.tools.open_add_expense_form import OpenAddExpenseFormInput, open_add_expense_form
from app.models.category import Category
from app.models.category_hint import CategoryHint
from app.models.expense import Expense
from app.models.user import User
from app.schemas.chat import ChatMessage, ChatRequest, ChatRole
from app.schemas.expense import ExpenseUpdate
from app.services import category_service, category_suggestion_service, expense_service
from app.services.chat_service import _build_system_prompt, _last_user_message

TODAY = date(2026, 11, 26)


def _category(session: Session, user: User, slug: str) -> Category:
    category = category_service.get_category_by_slug(session, user.id, slug)
    assert category
    return category


def _beauty(session: Session, user: User) -> Category:
    return category_service.create_category(session, user.id, "beauty", "Beleza", "💅")


def _add_expense(
    session: Session, user: User, category: Category, description: str, day: date = TODAY
) -> Expense:
    expense = Expense(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("35.00"),
        expense_date=day,
        description=description,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def _hints(session: Session, user: User) -> list[CategoryHint]:
    return list(session.exec(select(CategoryHint).where(CategoryHint.user_id == user.id)).all())


# ---------------------------------------------------------------------------
# Learning from corrections
# ---------------------------------------------------------------------------


def test_category_change_records_hint(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("hint@example.com")
    beauty = _beauty(session, user)
    expense = _add_expense(session, user, _category(session, user, "health"), "Consulta de pés")

    expense_service.update_expense(
        session, user.id, expense.id, ExpenseUpdate(category_id=beauty.id)
    )

    [hint] = _hints(session, user)
    assert hint.category_id == beauty.id
    assert hint.description_key == "consulta pe"
    assert hint.description == "Consulta de pés"
    assert hint.hit_count == 1


def test_update_without_category_change_records_nothing(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("nohint@example.com")
    expense = _add_expense(session, user, _category(session, user, "health"), "Consulta de pés")

    expense_service.update_expense(
        session, user.id, expense.id, ExpenseUpdate(amount=Decimal("40.00"))
    )

    assert _hints(session, user) == []


def test_repeated_corrections_strengthen_or_replace_hint(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("repeat@example.com")
    beauty = _beauty(session, user)
    health = _category(session, user, "health")
    first = _add_expense(session, user, health, "Consulta de pés")
    second = _add_expense(session, user, health, "consulta aos pés")

    expense_service.update_expense(session, user.id, first.id, ExpenseUpdate(category_id=beauty.id))
    expense_service.update_expense(
        session, user.id, second.id, ExpenseUpdate(category_id=beauty.id)
    )
    [hint] = _hints(session, user)
    assert hint.hit_count == 2

    expense_service.update_expense(session, user.id, first.id, ExpenseUpdate(category_id=health.id))
    [hint] = _hints(session, user)
    assert hint.category_id == health.id
    assert hint.hit_count == 1


def test_description_without_tokens_records_nothing(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("empty@example.com")
    expense = _add_expense(session, user, _category(session, user, "health"), "35€")

    expense_service.update_expense(
        session, user.id, expense.id, ExpenseUpdate(category_id=_category(session, user, "food").id)
    )

    assert _hints(session, user) == []


# ---------------------------------------------------------------------------
# Suggesting
# ---------------------------------------------------------------------------


def test_learned_hint_beats_history_majority(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("beats@example.com")
    beauty = _beauty(session, user)
    health = _category(session, user, "health")
    expenses = [_add_expense(session, user, health, "Consulta de pés") for _ in range(4)]

    expense_service.update_expense(
        session, user.id, expenses[0].id, ExpenseUpdate(category_id=beauty.id)
    )
    suggestion = category_suggestion_service.suggest_category(
        session, user.id, "consulta de pés 35€", today=TODAY
    )

    assert suggestion is not None
    assert suggestion.category.id == beauty.id
    assert suggestion.source == "learned"
    assert suggestion.confidence == 1.0


def test_hint_contained_in_longer_description_applies(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("contained@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    session.commit()

    suggestion = category_suggestion_service.suggest_category(
        session, user.id, "Consulta de pés na clínica Sorriso", today=TODAY
    )

    assert suggestion is not None
    assert suggestion.category.id == beauty.id
    assert suggestion.confidence == category_suggestion_service.CONTAINED_HINT_CONFIDENCE


def test_history_suggests_most_used_similar_category(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("history@example.com")
    food = _category(session, user, "food")
    _add_expense(session, user, food, "Almoço cantina")
    _add_expense(session, user, food, "almoço na cantina")
    _add_expense(session, user, _category(session, user, "transport"), "Uber")

    suggestion = category_suggestion_service.suggest_category(
        session, user.id, "Almoço cantina 7,50€", today=TODAY
    )

    assert suggestion is not None
    assert suggestion.category.id == food.id
    assert suggestion.source == "history"


def test_no_suggestion_when_nothing_similar(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("none@example.com")
    _add_expense(session, user, _category(session, user, "food"), "Almoço cantina")

    assert (
        category_suggestion_service.suggest_category(session, user.id, "Gasolina", today=TODAY)
        is None
    )


def test_archived_category_is_never_suggested(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("archived@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    beauty.is_active = False
    session.add(beauty)
    session.commit()

    assert (
        category_suggestion_service.suggest_category(
            session, user.id, "consulta de pés", today=TODAY
        )
        is None
    )


def test_suggestions_are_scoped_to_user(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    owner, _ = make_user("owner@example.com")
    other, _ = make_user("other@example.com")
    category_suggestion_service.record_correction(
        session, owner.id, "consulta de pés", _beauty(session, owner).id
    )
    _add_expense(session, owner, _category(session, owner, "health"), "consulta de pés")
    session.commit()

    assert (
        category_suggestion_service.suggest_category(
            session, other.id, "consulta de pés", today=TODAY
        )
        is None
    )


def test_deleting_unused_category_removes_its_hints(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("cascade@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    session.commit()

    result = category_service.delete_or_archive_category(session, user.id, beauty.id)

    assert result is not None and result.action == "deleted"
    session.expire_all()
    assert _hints(session, user) == []


# ---------------------------------------------------------------------------
# REST endpoint
# ---------------------------------------------------------------------------


def test_endpoint_learns_from_patch_and_suggests(
    client: TestClient, session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, headers = make_user("api@example.com")
    beauty = _beauty(session, user)
    health = _category(session, user, "health")
    created = client.post(
        "/api/v1/expenses",
        json={
            "amount": "35.00",
            "expense_date": "2026-11-20",
            "description": "Consulta de pés",
            "category_id": str(health.id),
        },
        headers=headers,
    ).json()

    patched = client.patch(
        f"/api/v1/expenses/{created['id']}",
        json={"category_id": str(beauty.id)},
        headers=headers,
    )
    assert patched.status_code == 200

    response = client.get(
        "/api/v1/expenses/category-suggestion",
        params={"description": "consulta aos pés"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"]["id"] == str(beauty.id)
    assert body["source"] == "learned"


def test_endpoint_returns_204_without_suggestion(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/expenses/category-suggestion",
        params={"description": "algo completamente novo"},
        headers=auth_headers,
    )
    assert response.status_code == 204


def test_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get(
        "/api/v1/expenses/category-suggestion", params={"description": "consulta"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Chat integration
# ---------------------------------------------------------------------------


def test_prompt_includes_learned_preferences(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("prompt@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "Consulta de pés", beauty.id)
    session.commit()

    hints = category_suggestion_service.hints_for_prompt(session, user.id, "consulta de pés 35€")
    prompt = _build_system_prompt(category_service.list_categories(session, user.id), "pt", hints)

    assert "Learned preferences" in prompt
    assert f'"Consulta de pés" → beauty (id: {beauty.id})' in prompt


def test_prompt_without_hints_has_no_learned_section(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("noprompt@example.com")
    prompt = _build_system_prompt(category_service.list_categories(session, user.id), "en", [])
    assert "Learned preferences" not in prompt


def test_hints_for_prompt_ranks_matching_hints_first(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("rank@example.com")
    beauty = _beauty(session, user)
    food = _category(session, user, "food")
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    category_suggestion_service.record_correction(session, user.id, "pastelaria", food.id)
    session.commit()

    hints = category_suggestion_service.hints_for_prompt(
        session, user.id, "regista uma consulta de pés", limit=1
    )

    assert [h.description for h, _ in hints] == ["consulta de pés"]


def test_last_user_message_picks_latest_user_turn() -> None:
    request = ChatRequest(
        messages=[
            ChatMessage(role=ChatRole.user, content="primeira"),
            ChatMessage(role=ChatRole.assistant, content="resposta"),
            ChatMessage(role=ChatRole.user, content="consulta de pés"),
            ChatMessage(role=ChatRole.assistant, content="ok"),
        ]
    )
    assert _last_user_message(request) == "consulta de pés"


def test_open_form_tool_falls_back_to_learned_category(
    session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, _ = make_user("formtool@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    session.commit()

    result = open_add_expense_form(
        session, user.id, OpenAddExpenseFormInput(description="Consulta de pés")
    )

    assert result["prefill"]["category_id"] == str(beauty.id)


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------


def _csv_upload(text: str) -> dict:
    return {
        "files": {"file": ("expenses.csv", text.encode("utf-8"), "text/csv")},
        "data": {"default_month": "2026-11"},
    }


def test_csv_rows_without_category_use_learned_category(
    client: TestClient, session: Session, make_user: Callable[[str], tuple[User, dict[str, str]]]
) -> None:
    user, headers = make_user("csv@example.com")
    beauty = _beauty(session, user)
    category_suggestion_service.record_correction(session, user.id, "consulta de pés", beauty.id)
    session.commit()
    text = (
        "date;description;amount;category\n"
        "2026-11-02;Consulta de pés;35,00;\n"  # no category -> learned
        "2026-11-03;Consulta de pés;35,00;Outros\n"  # explicit category is respected
        "2026-11-04;Algo novo;10,00;\n"  # nothing learned -> Other
    )

    preview = client.post(
        "/api/v1/import-export/import/preview", headers=headers, **_csv_upload(text)
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["inferred_categories"] == 1

    result = client.post("/api/v1/import-export/import", headers=headers, **_csv_upload(text))
    assert result.status_code == 201, result.text
    by_date = {
        e.expense_date.day: e.category_id
        for e in session.exec(select(Expense).where(Expense.user_id == user.id)).all()
    }
    other = _category(session, user, "other")
    assert by_date == {2: beauty.id, 3: other.id, 4: other.id}
