# Ledger — Personal Expense Tracker

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

Prerequisites: Python 3.11+, Node 20+, a running PostgreSQL with a database
matching `DATABASE_URL` in `.env`.

### Backend

```bash
cd backend
cp .env.example .env             # then edit values
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

Or just run the helper:

```bash
./scripts/setup_backend.sh
```

### Frontend

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

## How this evolves

The architecture was chosen so the two obvious next steps don't require
rewrites:

- **Mobile app** — see [`docs/MOBILE_EVOLUTION.md`](docs/MOBILE_EVOLUTION.md).
  The TypeScript types and most of the API client are directly portable to
  React Native (Expo). The backend is already API-first; only refresh tokens
  and optional push-notification endpoints need adding.

- **LLM / chatbot** — see [`docs/LLM_INTEGRATION.md`](docs/LLM_INTEGRATION.md).
  The `app/llm/` module already exposes a `Tool` registry with OpenAI and
  Anthropic schema converters, plus two ready handlers (`search_expenses`,
  `add_expense`) that call straight into the service layer. Wiring an actual
  chat endpoint is purely additive — no existing code needs to change.

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
