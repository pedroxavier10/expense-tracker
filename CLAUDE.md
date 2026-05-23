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
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
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

Key FastAPI dependencies injected everywhere:
- `SessionDep` — yields a SQLModel `Session`
- `CurrentUser` — extracts authenticated user from JWT

### Frontend (`frontend/src/`)

- **`lib/api.ts`** — Single fetch wrapper; injects Bearer token from `localStorage`; throws `ApiError` on failure
- **`types/api.ts`** — Hand-written TypeScript mirrors of backend Pydantic schemas; keep in sync manually
- **`components/`** — `AuthProvider` (context), `Dashboard` (main coordinator), `ExpenseForm`, `ExpenseList`, `FilterBar`, `LoginForm`
- **`app/`** — Next.js App Router; `layout.tsx` sets fonts, `page.tsx` wraps Dashboard in AuthProvider

### API endpoints
```
POST   /api/v1/auth/login/json        # JSON login (SPA)
GET    /api/v1/auth/me
GET    /api/v1/expenses               # filters: category_id, month, date_from, date_to, description_contains, limit, offset
POST   /api/v1/expenses
PATCH  /api/v1/expenses/{id}
DELETE /api/v1/expenses/{id}
GET    /api/v1/categories
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
