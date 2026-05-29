# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack personal expense tracker: FastAPI backend (Python 3.11+) + Next.js 15 frontend (TypeScript). Designed to evolve into a mobile app and LLM chatbot without rewrites.

## Development Commands

### Docker (recommended)
```bash
docker compose up --build
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Backend (no Docker)
```bash
cd backend
cp .env.example .env             # then edit values
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

### Frontend (no Docker)
```bash
cd frontend
npm install
npm run dev
```

### Backend tests (in-memory SQLite, no PostgreSQL needed)
```bash
cd backend
pytest                            # all tests
pytest app/tests/test_expenses.py # single file
pytest -k "test_create"           # single test by name
```

### Frontend checks
```bash
cd frontend
npm run type-check
npm run lint
npm run build
```

### Database migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture

### Backend (`backend/app/`)

Strict three-layer pattern — do not skip layers:
```
endpoints (api/v1/endpoints/)  →  services (services/)  →  models (models/)
```
- **`endpoints/`** — Thin HTTP layer only; no business logic
- **`services/`** — All business logic; returns `None` on not-found (never raises)
- **`models/`** — SQLModel ORM classes (DB table definitions)
- **`schemas/`** — Pydantic DTOs used by endpoints and LLM tools
- **`core/`** — Settings (`config.py`) and JWT/bcrypt security
- **`db/`** — Engine, session factory, seed data
- **`llm/`** — Tool registry + OpenAI/Anthropic format converters (ready for chatbot)
- **`scheduler.py`** — APScheduler background job; materializes all active recurring expense rules on day 1 of each month at 02:00 UTC

Key FastAPI dependencies injected everywhere:
- `SessionDep` — yields a SQLModel `Session`
- `CurrentUser` — extracts authenticated user from JWT

### Frontend (`frontend/src/`)

- **`lib/api.ts`** — Single fetch wrapper; injects Bearer token from `localStorage`; throws `ApiError` on failure
- **`types/api.ts`** — Hand-written TypeScript mirrors of backend Pydantic schemas; keep in sync manually
- **`hooks/`** — Data-fetching hooks (`useExpenses`, `useRecurringExpenses`, `useCategories`, …)
- **`components/auth/`** — `AuthProvider` (context), `LoginForm`
- **`components/layout/`** — `AppShell`, `Sidebar`
- **`components/expenses/`** — `ExpenseForm`, `ExpenseList`, `FilterBar`, `AddExpenseModal`
- **`components/recurring/`** — `RecurringExpenseList`, `RecurringExpenseForm`, `AddRecurringExpenseModal`, `MaterializeConfirmStep`
- **`components/chat/`** — `ChatPanel`, `ChatFAB`, `ChatActionsProvider`
- **`components/categories/`** — `CategoryList`
- **`components/reports/`** — `ReportsCharts`, `SummaryCard`
- **`app/(auth)/`** — Login route (unauthenticated layout)
- **`app/(app)/`** — Authenticated route group: `dashboard/`, `expenses/`, `recurring/`, `categories/`, `reports/`, `chat/`
- **`messages/`** — `en.json` / `pt.json` translation namespaces consumed by `next-intl`

### API endpoints
```
POST   /api/v1/auth/login/json        # JSON login (SPA)
GET    /api/v1/auth/me
PATCH  /api/v1/auth/me                # update current-user preferences (e.g. {"language": "pt"})
GET    /api/v1/expenses               # filters: category_id, month, date_from, date_to, description_contains, limit, offset
POST   /api/v1/expenses
PATCH  /api/v1/expenses/{id}
DELETE /api/v1/expenses/{id}
GET    /api/v1/categories
GET    /api/v1/recurring-expenses
POST   /api/v1/recurring-expenses
GET    /api/v1/recurring-expenses/{rule_id}
PATCH  /api/v1/recurring-expenses/{rule_id}
DELETE /api/v1/recurring-expenses/{rule_id}
POST   /api/v1/recurring-expenses/{rule_id}/materialize-current-month  # creates the expense for the current month; 409 if already exists or rule inactive
```

## Key Conventions

**Python:**
- Imports: always absolute (`from app.services.expense_service import ...`)
- Type hints: PEP 604 style (`str | None`, not `Optional[str]`)
- Datetimes: always UTC (`datetime.now(UTC)`)
- Money: `Numeric(12, 2)` in DB, `Decimal` in Python, `str` on the JSON wire — never `float`
- Dates: plain `DATE` column (no time component) to avoid timezone bugs
- Errors: endpoints raise `HTTPException`; services return `None`

**TypeScript:**
- All monetary amounts arrive as strings from the API
- Dates are ISO `YYYY-MM-DD` strings

**Internationalization:**
- Two locales supported: `en` (default) and `pt` (European Portuguese)
- Strings live in `frontend/messages/{en,pt}.json`, grouped by namespace (`common`, `sidebar`, `dashboard`, `expenses`, `chat`, …)
- Components read strings via `useTranslations("namespace")` from `next-intl`; never hardcode user-facing text
- Locale state is managed by `LocaleProvider` (`components/LocaleProvider.tsx`) — `useLocale()` exposes `{ locale, setLocale }`
- For locale-aware currency/date use `useFormat()` (`lib/useFormat.ts`) instead of the static `formatCurrency` / `formatDate`
- The selected locale is persisted on `users.language` and mirrored to `localStorage["app_locale"]`; the chat system prompt picks the locale from there too

## Project-Local Agents and Skills

The `.claude/` directory defines specialized agents and skills. Use them for:

| Task | What to use |
|------|-------------|
| Adding backend endpoints, services, models, or LLM tools | `expense-domain` skill (auto-loaded) |
| Adding frontend API calls, types, or components | `api-integration` skill (auto-loaded) |
| Writing an Alembic migration after model changes | `migration-author` agent |
| Adding a new LLM tool end-to-end | `llm-tool-author` agent |

## Default Credentials
- Email: `me@example.com` / Password: `changeme` (override via `.env` or `docker-compose.yml`)
