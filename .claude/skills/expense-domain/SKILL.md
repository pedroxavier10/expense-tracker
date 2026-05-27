---
name: expense-domain
description: Use this skill when adding new functionality to the Expense Tracker backend — new endpoints, new models, new services, or new LLM tools. It encodes the project's layering conventions so additions stay consistent. Trigger this skill any time you would touch files under `backend/app/` to add behaviour rather than fix a bug.
---

# Expense Tracker — Adding Backend Features

This project uses a strict three-layer separation:

```
endpoints  →  services  →  models
   ↑              ↑
   └── schemas    └── (LLM tools also call services directly)
```

**Never skip the service layer.** Endpoints should be thin: parse input,
call a service, map results into a schema. All business logic, database
access, and cross-entity orchestration go in services.

## Adding a new endpoint

1. **Schema** (`app/schemas/<entity>.py`): define `*Create`, `*Update`,
   `*Read`, and any filter models. Use `model_config = ConfigDict(from_attributes=True)`
   on read models so they can be built from ORM rows.

2. **Service** (`app/services/<entity>_service.py`): add pure functions that
   take a `Session` plus typed inputs. Functions return ORM models or
   primitives — never `HTTPException`. Raising HTTP errors is the
   endpoint's job.

3. **Endpoint** (`app/api/v1/endpoints/<entity>.py`): one router per entity.
   Use `SessionDep`, `CurrentUser` dependencies. Map service results into
   schemas with `Schema.model_validate(obj)`.

4. **Register** the router in `app/api/v1/router.py`.

5. **Tests** in `app/tests/test_<entity>.py`. Use the `client` and
   `auth_headers` fixtures from `conftest.py`.

## Adding a new model

1. Create the SQLModel class in `app/models/<entity>.py` with
   `table=True`. UUID primary key (`Field(default_factory=uuid4)`),
   `Numeric(12, 2)` for money, `DATE` for day-level dates.

2. Import it in `app/models/__init__.py` so Alembic autogenerate sees it.

3. Generate a migration: `alembic revision --autogenerate -m "add <entity>"`.
   Review the generated file before committing — autogenerate is good but
   not perfect (it often misses index renames, enum changes).

4. Apply: `alembic upgrade head`.

## Adding a new LLM tool

See `docs/LLM_INTEGRATION.md` for the full pattern. Short version:

1. New file in `app/llm/tools/<tool_name>.py` with a Pydantic input model
   and a handler `def my_tool(session, user_id, payload) -> dict:`.
2. Register in `app/llm/tools/__init__.py`'s `REGISTRY`.
3. **The handler must call `app.services.*` functions** — never inline
   queries. This guarantees the LLM gets the same behaviour as the REST API.
4. **Never accept `user_id` from the LLM.** It's always injected by the
   caller from the authenticated session.

## Conventions

- Imports: `from app.X import Y` (absolute), never relative.
- Type hints: PEP 604 unions (`str | None`), never `Optional[str]`.
- Datetimes: always timezone-aware (`datetime.now(UTC)`), stored as UTC.
- Errors: raise `HTTPException` in endpoints, return `None` from services.
- Tests: arrange-act-assert, one behaviour per test, use the in-memory
  SQLite fixtures.

## User preferences

`User.language` (Literal `"en" | "pt"`, default `"en"`) is updated via
`PATCH /api/v1/auth/me` with a `UserUpdate` schema. The schema is
intentionally partial so future preferences (theme, notifications, …) can
be added without breaking the contract. `chat_service._build_system_prompt`
takes the language as an argument and substitutes a locale instruction
(`LOCALE_INSTRUCTION[lang]`) into the prompt template — so the chat bot
answers in the user's chosen language without any extra round-trip.

## Running locally after changes

```bash
cd backend
source .venv/bin/activate
alembic upgrade head        # if you added migrations
pytest                      # run tests
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` to interactively test new endpoints.
