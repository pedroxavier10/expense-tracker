"""Category hints endpoints: list, change category, delete (the "O que aprendi" screen)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.category import Category
from app.models.category_hint import CategoryHint
from app.models.user import User
from app.services import category_service, category_suggestion_service

HINTS = "/api/v1/category-hints"

MakeUser = Callable[[str], tuple[User, dict[str, str]]]


def _category(session: Session, user: User, slug: str) -> Category:
    category = category_service.get_category_by_slug(session, user.id, slug)
    assert category
    return category


def _hint(session: Session, user: User, description: str, category: Category) -> CategoryHint:
    hint = category_suggestion_service.record_correction(session, user.id, description, category.id)
    assert hint
    session.commit()
    session.refresh(hint)
    return hint


def test_list_hints_most_recent_first(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("list@example.com")
    _hint(session, user, "Pastelaria", _category(session, user, "food"))
    _hint(session, user, "Consulta de pés", _category(session, user, "health"))

    response = client.get(HINTS, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [h["description"] for h in body] == ["Consulta de pés", "Pastelaria"]
    assert body[0]["category"]["slug"] == "health"
    assert body[0]["hit_count"] == 1


def test_list_includes_hints_of_archived_categories(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("archived@example.com")
    leisure = _category(session, user, "leisure")
    _hint(session, user, "Cinema", leisure)
    leisure.is_active = False
    session.add(leisure)
    session.commit()

    [hint] = client.get(HINTS, headers=headers).json()

    assert hint["category"]["is_active"] is False


def test_update_hint_category_changes_suggestion(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("update@example.com")
    health = _category(session, user, "health")
    leisure = _category(session, user, "leisure")
    hint = _hint(session, user, "Consulta de pés", health)
    _hint(session, user, "consulta aos pés", health)  # same key -> hit_count 2

    response = client.patch(
        f"{HINTS}/{hint.id}", json={"category_id": str(leisure.id)}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"]["id"] == str(leisure.id)
    assert body["hit_count"] == 1
    suggestion = category_suggestion_service.suggest_category(session, user.id, "consulta pés")
    assert suggestion is not None and suggestion.category.id == leisure.id


def test_update_hint_rejects_foreign_or_archived_category(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("owner@example.com")
    other, _ = make_user("other@example.com")
    hint = _hint(session, user, "Consulta de pés", _category(session, user, "health"))
    archived = _category(session, user, "leisure")
    archived.is_active = False
    session.add(archived)
    session.commit()

    for category in (_category(session, other, "leisure"), archived):
        response = client.patch(
            f"{HINTS}/{hint.id}", json={"category_id": str(category.id)}, headers=headers
        )
        assert response.status_code == 404


def test_delete_hint_forgets_it(client: TestClient, session: Session, make_user: MakeUser) -> None:
    user, headers = make_user("delete@example.com")
    hint = _hint(session, user, "Consulta de pés", _category(session, user, "leisure"))

    response = client.delete(f"{HINTS}/{hint.id}", headers=headers)

    assert response.status_code == 204
    assert client.get(HINTS, headers=headers).json() == []
    assert category_suggestion_service.suggest_category(session, user.id, "consulta de pés") is None


def test_hints_are_isolated_between_users(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    owner, _ = make_user("a@example.com")
    _, intruder_headers = make_user("b@example.com")
    hint = _hint(session, owner, "Consulta de pés", _category(session, owner, "health"))
    intruder_category = category_service.list_categories(session, owner.id)[0]

    assert client.get(HINTS, headers=intruder_headers).json() == []
    assert client.delete(f"{HINTS}/{hint.id}", headers=intruder_headers).status_code == 404
    patch = client.patch(
        f"{HINTS}/{hint.id}",
        json={"category_id": str(intruder_category.id)},
        headers=intruder_headers,
    )
    assert patch.status_code == 404
    session.expire_all()
    assert session.get(CategoryHint, hint.id) is not None


def test_requires_auth(client: TestClient) -> None:
    assert client.get(HINTS).status_code == 401
