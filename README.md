# Ledger-x — Personal Expense Tracker

A small, well-built full-stack expense tracker for personal use. Designed
to grow into a mobile app and gain a natural-language interface without
rewrites.

```
┌─────────────┐     HTTP/JSON      ┌──────────────┐     SQL      ┌────────────┐
│  Next.js    │ ─────────────────► │   FastAPI    │ ───────────► │ PostgreSQL │
│  (web app)  │                    │   (API-first)│              │            │
└─────────────┘                    └──────────────┘              └────────────┘
                                          │
                                          │  same service layer
                                          ▼
                                   ┌──────────────┐
                                   │  app/llm/    │  ← tool registry, ready for
                                   │  (scaffold)  │     OpenAI / Anthropic later
                                   └──────────────┘
```

## What it does

- Create, read, update, delete expenses.
- Filter by category, single month, custom date range, and description text.
- Track an amount, date, description, and category per expense.
- Eight seeded categories: food, transport, health, home, leisure, shopping,
  work, other.

## Stack

| Layer    | Choice                                          |
| -------- | ----------------------------------------------- |
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind |
| i18n     | **next-intl** (EN + PT, runtime switching)      |
| Backend  | FastAPI, Python 3.11+                           |
| ORM      | **SQLModel** (SQLAlchemy 2.0 + Pydantic)        |
| Database | PostgreSQL 16                                   |
| Auth     | JWT (HS256) + bcrypt                            |
| Migrations | Alembic                                       |
| Tests    | pytest (in-memory SQLite for speed)             |
| Container | Docker + docker-compose                        |

## Project layout

```
expense-tracker/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # HTTP layer (thin)
│   │   ├── core/                # config, security
│   │   ├── db/                  # engine, session, seed
│   │   ├── models/              # SQLModel tables
│   │   ├── schemas/             # Pydantic DTOs
│   │   ├── services/            # business logic
│   │   ├── llm/                 # LLM scaffold (tools, registry)
│   │   └── tests/
│   ├── alembic/                 # migrations
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/          # React components
│   │   ├── lib/                 # API client, formatters
│   │   └── types/               # shared TS types
│   ├── Dockerfile
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md          # decisions and rationale
│   ├── LLM_INTEGRATION.md       # how to wire the chatbot later
│   └── MOBILE_EVOLUTION.md      # how to add a mobile client
├── .claude/                     # project-local skills + agents
├── scripts/                     # dev helpers
└── docker-compose.yml
```

## Quick start with Docker (recommended)

```bash
git clone <this-repo>
cd expense-tracker
docker compose up --build
```

Then:

- Web app: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- OpenAPI: <http://localhost:8000/api/v1/openapi.json>

Default login (from `docker-compose.yml`):

- email: `me@example.com`
- password: `changeme`

To change them, set `DEFAULT_USER_EMAIL` and `DEFAULT_USER_PASSWORD` before
running `docker compose up`. **Change `SECRET_KEY` before deploying anywhere.**

## Quick start without Docker

**Prerequisites:** Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Node 20+, PostgreSQL 16.

### 1. Database

**Option A — only the database in Docker (recommended for local dev):**

```bash
docker compose up db
```

This starts PostgreSQL mapped to port **5466** on your machine, which matches
the default `DATABASE_URL` in `.env.example`. No further database setup needed.

**Option B — PostgreSQL installed locally:**

Create the user and database (adjust port in `.env` to match your installation):

```sql
CREATE USER expense_user WITH PASSWORD 'expense_pass';
CREATE DATABASE expense_tracker OWNER expense_user;
```

Then edit `backend/.env` and set `DATABASE_URL` to use the correct host and port
(typically `5432` for a default PostgreSQL installation).

### 2. Backend

```bash
cd backend
cp .env.example .env             # edit values if needed
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

Or just run the helper (uses `uv` internally):

```bash
./scripts/setup_backend.sh
```

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Tests use in-memory SQLite, so you don't need PostgreSQL running for them.

## Why SQLModel?

This was the most consequential ORM choice — full rationale in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Short version: SQLModel was
built by the FastAPI author and combines SQLAlchemy 2.0 (mature ORM) with
Pydantic (validation), so the same class powers both the database row and
the API schema where appropriate. You don't lose anything — SQLModel models
*are* SQLAlchemy models, so the full SQLAlchemy API is available when you
need it. The alternative, plain SQLAlchemy + separate Pydantic schemas,
gives more flexibility at the cost of duplicating every field definition;
overkill for a project this size.

## Translations

The app ships in **English** (default) and **European Portuguese**. The
language toggle (`EN` / `PT`) lives in the sidebar footer. Choosing a
language:

1. Updates the UI immediately (no page reload).
2. Persists to the logged-in user's account via `PATCH /api/v1/auth/me`, so
   the preference survives across devices and browser sessions.
3. Tells the chat bot to reply in the same language.

**Adding a new user-facing string:**

1. Add the key + English text to `frontend/messages/en.json` under the
   appropriate namespace, then the same key + Portuguese text to
   `frontend/messages/pt.json`. Both files must stay in sync — a missing key
   throws at render time.
2. Use it in any client component:
   ```tsx
   import { useTranslations } from "next-intl";
   const t = useTranslations("expenses");
   <button>{t("addExpense")}</button>
   ```

**Adding a third language** requires: a new `frontend/messages/<code>.json`
file, adding the code to `SUPPORTED_LOCALES` in `frontend/src/lib/i18n.ts`,
and adding a `LOCALE_INSTRUCTION` entry in
`backend/app/services/chat_service.py`. No schema migration needed.

## Built-in CRUD endpoints

```
GET    /api/v1/expenses                  # list with filters
POST   /api/v1/expenses                  # create
GET    /api/v1/expenses/{id}             # get one
PATCH  /api/v1/expenses/{id}             # update
DELETE /api/v1/expenses/{id}             # delete

GET    /api/v1/categories                # list all seeded categories

POST   /api/v1/auth/login                # OAuth2 form (for Swagger UI)
POST   /api/v1/auth/login/json           # JSON body (for SPA / mobile)
GET    /api/v1/auth/me                   # current user
PATCH  /api/v1/auth/me                   # update user preferences (e.g. language)

POST   /api/v1/chat                      # LLM chat with tool use
```

All `/expenses` and `/categories` endpoints require `Authorization: Bearer <token>`.

### Available filters on `GET /expenses`

| Param                  | Notes                                                |
| ---------------------- | ---------------------------------------------------- |
| `category_id`          | UUID                                                 |
| `category_slug`        | e.g. `food` (useful for the LLM layer)               |
| `month`                | `YYYY-MM`, mutually exclusive with `date_from/to`    |
| `date_from`            | inclusive lower bound                                |
| `date_to`              | inclusive upper bound                                |
| `description_contains` | case-insensitive substring                           |
| `limit`                | 1–500, default 100                                   |
| `offset`               | for pagination                                       |

## Personal-use deliberate omissions

These are intentionally **not** in the project, because they'd be
overengineering for personal use. Each has an obvious path to add later:

- No public registration endpoint (default user is seeded). Add a
  `/auth/register` endpoint when needed.
- No refresh tokens (7-day access token instead). Add when the mobile app
  arrives.
- No budgets, savings goals, or recurring expenses. The model is generic
  enough to add these as new entities without refactoring.
- No currency conversion (everything assumed EUR for display). Add a
  `currency` column on `Expense` when needed.
- No CSV import. A 20-line script can be added under `scripts/` when needed.

## Architecture decisions

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a numbered list of
choices and the reasoning behind each.

## Working with Claude on this codebase

The `.claude/` directory contains project-local skills and agents that
encode the conventions:

- `skills/expense-domain` — how to add endpoints, models, services, tools
- `skills/api-integration` — how the frontend talks to the API
- `agents/migration-author` — generates Alembic migrations
- `agents/llm-tool-author` — adds new LLM tools end-to-end

These get picked up automatically by Claude Code / Claude.ai when you work
in this repo.

## License

Personal project. Do what you want with it.
