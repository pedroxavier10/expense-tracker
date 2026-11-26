"""Import/export endpoint tests: preview, category creation, duplicates, export."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.category import Category
from app.models.expense import Expense
from app.models.user import User
from app.services import slug_service

PREVIEW = "/api/v1/import-export/import/preview"
IMPORT = "/api/v1/import-export/import"
EXPORT = "/api/v1/import-export/export"

MakeUser = Callable[[str], tuple[User, dict[str, str]]]


@pytest.fixture(autouse=True)
def _force_local_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_llm(_name: str, _existing: set[str]) -> str:
        return ""

    monkeypatch.setattr(slug_service, "_llm_suggest_slug", _no_llm)


def _upload(text: str, **form: str) -> dict:
    return {
        "files": {"file": ("expenses.csv", text.encode("utf-8"), "text/csv")},
        "data": {"default_month": "2026-03", **form},
    }


def _csv(*rows: str) -> str:
    return "date;description;amount;category\n" + "\n".join(rows) + "\n"


def _expenses(session: Session, user: User) -> list[Expense]:
    return list(session.exec(select(Expense).where(Expense.user_id == user.id)).all())


def _category(session: Session, user: User, slug: str) -> Category | None:
    stmt = select(Category).where(Category.user_id == user.id, Category.slug == slug)
    return session.exec(stmt).first()


def test_preview_writes_nothing(client: TestClient, session: Session, make_user: MakeUser) -> None:
    user, headers = make_user("a@example.com")
    text = _csv("2026-01-15;Café;1,20;Food", "2026-01;Ginásio;42,19;Mensalidades", ";X;-5;")
    resp = client.post(PREVIEW, headers=headers, **_upload(text))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_rows"] == 3
    assert body["valid_rows"] == 2
    assert body["invalid_rows"] == [{"line": 4, "code": "non_positive_amount", "value": "-5"}]
    assert body["new_categories"] == ["Mensalidades"]
    assert body["duplicates"] == 0
    assert body["requires_confirmation"] is False
    assert body["total_amount"] == "43.39"
    assert _expenses(session, user) == []
    assert _category(session, user, "mensalidades") is None


def test_import_creates_categories_and_applies_defaults(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    text = _csv(
        "2026-01-15;Café;1,20;food",  # matched by slug
        "2026-01;;42,19;Mensalidades",  # new category, empty description
        ";Pão;0,90;",  # no date, no category
        "2026-01-02;Bad;abc;Food",  # invalid -> skipped
    )
    resp = client.post(IMPORT, headers=headers, **_upload(text))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["imported"] == 3
    assert body["skipped_invalid"] == 1
    assert [c["name"] for c in body["created_categories"]] == ["Mensalidades"]

    by_desc = {e.description: e for e in _expenses(session, user)}
    assert set(by_desc) == {"Café", "Mensalidades", "Pão"}
    assert by_desc["Mensalidades"].expense_date.isoformat() == "2026-01-01"
    assert by_desc["Pão"].expense_date.isoformat() == "2026-03-01"
    other = _category(session, user, "other")
    assert other is not None
    assert by_desc["Pão"].category_id == other.id


def test_category_match_is_case_and_accent_insensitive(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    client.post("/api/v1/categories", headers=headers, json={"name": "Saúde Mental"})
    resp = client.post(IMPORT, headers=headers, **_upload(_csv("2026-01-01;X;5;saude mental")))
    assert resp.status_code == 201
    assert resp.json()["created_categories"] == []


def test_missing_other_is_recreated_in_user_language(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    user.language = "pt"
    session.add(user)
    other = _category(session, user, "other")
    assert other is not None
    session.delete(other)
    session.commit()

    resp = client.post(IMPORT, headers=headers, **_upload(_csv(";X;5;")))
    assert resp.status_code == 201
    [created] = resp.json()["created_categories"]
    assert (created["slug"], created["name"]) == ("other", "Outros")


def test_archived_other_is_reactivated(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    other = _category(session, user, "other")
    assert other is not None
    other.is_active = False
    session.add(other)
    session.commit()

    preview = client.post(PREVIEW, headers=headers, **_upload(_csv(";X;5;"))).json()
    assert preview["reactivated_categories"] == ["Other"]
    assert preview["new_categories"] == []

    resp = client.post(IMPORT, headers=headers, **_upload(_csv(";X;5;")))
    assert resp.status_code == 201
    session.refresh(other)
    assert other.is_active is True


def _seed_duplicates(client: TestClient, headers: dict[str, str], n: int) -> str:
    rows = [f"2026-01-01;Lanche {i};{i + 1},00;Food" for i in range(n)]
    resp = client.post(IMPORT, headers=headers, **_upload(_csv(*rows)))
    assert resp.status_code == 201
    return _csv(*rows)


def test_below_threshold_imports_without_confirmation(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    text = _seed_duplicates(client, headers, 9)
    preview = client.post(PREVIEW, headers=headers, **_upload(text)).json()
    assert (preview["duplicates"], preview["requires_confirmation"]) == (9, False)
    resp = client.post(IMPORT, headers=headers, **_upload(text))
    assert resp.status_code == 201
    assert len(_expenses(session, user)) == 18


def test_threshold_requires_confirmation(
    client: TestClient, session: Session, make_user: MakeUser
) -> None:
    user, headers = make_user("a@example.com")
    text = _seed_duplicates(client, headers, 10) + "2026-01-02;Novo;99,00;Food\n"

    preview = client.post(PREVIEW, headers=headers, **_upload(text)).json()
    assert (preview["duplicates"], preview["requires_confirmation"]) == (10, True)

    resp = client.post(IMPORT, headers=headers, **_upload(text))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "duplicates_confirmation_required"
    assert len(_expenses(session, user)) == 10

    resp = client.post(
        IMPORT,
        headers=headers,
        **_upload(text, confirm_duplicates="true", duplicate_mode="skip"),
    )
    assert resp.status_code == 201
    assert (resp.json()["imported"], resp.json()["skipped_duplicates"]) == (1, 10)
    assert len(_expenses(session, user)) == 11

    resp = client.post(
        IMPORT,
        headers=headers,
        **_upload(text, confirm_duplicates="true", duplicate_mode="import"),
    )
    assert resp.status_code == 201
    assert resp.json()["imported"] == 11
    assert len(_expenses(session, user)) == 22


def test_duplicates_require_same_category(client: TestClient, make_user: MakeUser) -> None:
    _, headers = make_user("a@example.com")
    _seed_duplicates(client, headers, 10)
    rows = [f"2026-01-01;Lanche {i};{i + 1},00;Transport" for i in range(10)]
    preview = client.post(PREVIEW, headers=headers, **_upload(_csv(*rows))).json()
    assert preview["duplicates"] == 0


def test_import_is_atomic(
    client: TestClient, session: Session, make_user: MakeUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, headers = make_user("a@example.com")
    categories_before = len(session.exec(select(Category)).all())

    def _boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(session, "commit", _boom)
    text = _csv("2026-01-01;X;5;Nova", "2026-01-01;Y;6;Food")
    with pytest.raises(RuntimeError):
        client.post(IMPORT, headers=headers, **_upload(text))
    monkeypatch.undo()

    assert _expenses(session, user) == []
    assert len(session.exec(select(Category)).all()) == categories_before


@pytest.mark.parametrize(
    ("text", "status", "detail"),
    [
        ("date;description\n2026-01-01;X\n", 400, "csv_missing_amount_column"),
        ("", 400, "csv_empty"),
    ],
)
def test_file_errors(
    client: TestClient, auth_headers: dict[str, str], text: str, status: int, detail: str
) -> None:
    resp = client.post(PREVIEW, headers=auth_headers, **_upload(text))
    assert resp.status_code == status
    assert resp.json()["detail"] == detail


def test_file_too_large(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import csv_service

    monkeypatch.setattr(csv_service, "MAX_FILE_BYTES", 10)
    resp = client.post(PREVIEW, headers=auth_headers, **_upload(_csv("2026-01-01;X;5;")))
    assert resp.status_code == 413


def test_requires_auth(client: TestClient) -> None:
    assert client.post(PREVIEW, **_upload(_csv(";X;5;"))).status_code == 401
    assert client.get(EXPORT).status_code == 401


def test_export_range_and_format(client: TestClient, make_user: MakeUser) -> None:
    _, headers = make_user("a@example.com")
    text = _csv(
        "2025-12-31;Old;1,00;Food",
        "2026-01-15;=HYPERLINK(x);23,45;Food",
        "2026-02-01;Gym;42,19;Mensalidades",
    )
    client.post(IMPORT, headers=headers, **_upload(text))

    resp = client.get(
        EXPORT, headers=headers, params={"date_from": "2026-01-01", "date_to": "2026-12-31"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "expenses_2026-01-01_2026-12-31.csv" in resp.headers["content-disposition"]
    content = resp.content.decode("utf-8")
    assert content.startswith("﻿")
    assert content.splitlines() == [
        "﻿date;description;amount;category",
        "2026-01-15;'=HYPERLINK(x);23,45;Food",
        "2026-02-01;Gym;42,19;Mensalidades",
    ]


def test_export_defaults_to_current_year(client: TestClient, make_user: MakeUser) -> None:
    _, headers = make_user("a@example.com")
    year = datetime.now(UTC).year
    text = _csv(f"{year}-06-01;This year;1;Food", f"{year - 1}-06-01;Last year;1;Food")
    client.post(IMPORT, headers=headers, **_upload(text))
    content = client.get(EXPORT, headers=headers).content.decode("utf-8")
    assert "This year" in content
    assert "Last year" not in content


def test_export_invalid_range(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get(
        EXPORT, headers=auth_headers, params={"date_from": "2026-02-01", "date_to": "2026-01-01"}
    )
    assert resp.status_code == 422


def test_export_then_reimport_is_all_duplicates(client: TestClient, make_user: MakeUser) -> None:
    _, headers = make_user("a@example.com")
    rows = [f"2026-01-{d:02d};Item {d};{d},50;Food" for d in range(1, 13)]
    client.post(IMPORT, headers=headers, **_upload(_csv(*rows)))
    exported = client.get(
        EXPORT, headers=headers, params={"date_from": "2026-01-01", "date_to": "2026-12-31"}
    ).content.decode("utf-8")

    preview = client.post(PREVIEW, headers=headers, **_upload(exported)).json()
    assert (preview["valid_rows"], preview["duplicates"]) == (12, 12)
    assert preview["requires_confirmation"] is True


def test_template_download(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/import-export/template", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content.decode("utf-8").startswith("﻿date;description;amount;category")


def test_user_isolation(client: TestClient, session: Session, make_user: MakeUser) -> None:
    _, headers_a = make_user("a@example.com")
    user_b, headers_b = make_user("b@example.com")
    rows = [f"2026-01-01;Secret {i};{i + 1},00;Food" for i in range(10)]
    client.post(IMPORT, headers=headers_a, **_upload(_csv(*rows)))

    exported = client.get(
        EXPORT, headers=headers_b, params={"date_from": "2026-01-01", "date_to": "2026-12-31"}
    ).content.decode("utf-8")
    assert "Secret" not in exported

    preview = client.post(PREVIEW, headers=headers_b, **_upload(_csv(*rows))).json()
    assert preview["duplicates"] == 0
    resp = client.post(IMPORT, headers=headers_b, **_upload(_csv(*rows)))
    assert resp.status_code == 201
    assert all(e.category.user_id == user_b.id for e in _expenses(session, user_b))
