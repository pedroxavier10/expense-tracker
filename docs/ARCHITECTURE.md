# Architecture Decisions

A short, opinionated log of the choices made and why. Update this when you
make significant changes — future you (and any LLM coding assistants) will
thank present you.

## 1. Monorepo, not microservices

One repo with `backend/`, `frontend/`, and `docs/`. The two services
communicate over HTTP. This is the right baseline for a personal project
because:

- One mental model.
- Atomic commits across server and client.
- Zero deployment complexity.

If you ever extract the LLM layer into its own service, the natural split
point is already there (`app/llm/` is self-contained).

## 2. SQLModel (over Tortoise, over SQLAlchemy + Pydantic separately)

We use **SQLModel** for the database layer.

**Why:**

- Built by the FastAPI author specifically for FastAPI use cases.
- Combines SQLAlchemy 2.0 (mature, full-featured ORM) with Pydantic
  (validation, JSON schema) — one class definition serves both, without the
  duplication of writing a SQLAlchemy model *and* a Pydantic schema for
  the same table.
- You don't lose anything: SQLModel models *are* SQLAlchemy models. You can
  drop down to raw SQLAlchemy for complex queries (we already do, e.g.
  `func.count()`, `func.lower()`).
- Works seamlessly with Alembic for migrations.

**Alternatives considered:**

- **SQLAlchemy + separate Pydantic schemas.** More flexible but
  more code. Worth it for very large teams; overkill here.
- **Tortoise ORM.** Async-native and ergonomic, but smaller ecosystem,
  weaker migration story (Aerich is fine but Alembic is the standard),
  and integration with Pydantic is bolted on.
- **SQLAlchemy + sqlacodegen.** Database-first; we wanted code-first.

**When to reconsider:** if SQLModel's pace of releases ever stalls
significantly relative to SQLAlchemy/Pydantic, switching to plain
SQLAlchemy + separate Pydantic schemas is straightforward — the service
layer would absorb 90% of the change.

## 3. Service layer between endpoints and ORM

Endpoints (`app/api/v1/endpoints/`) only handle HTTP concerns: parsing
inputs, mapping errors, returning DTOs. Business logic lives in
`app/services/`.

**Why this matters here:** the LLM tool layer (`app/llm/tools/`) calls into
the *same* service functions. If the logic lived in the endpoints, we'd
either duplicate it or invoke our own HTTP API from inside the process,
which is silly. Centralizing it once makes the LLM integration trivial.

## 4. Filters as a Pydantic model, not loose query params

`ExpenseFilters` is a Pydantic model with cross-field validation (e.g.
`month` is mutually exclusive with `date_from`/`date_to`). The HTTP layer
builds one from query params; the LLM tool layer builds one from the model's
output. Same object, same validation, same query.

## 5. JWT auth (HS256), 7-day token

- HS256 because there's a single signing party.
- 7 days because this is a personal app on a single device most of the time
  and constant logins are annoying. For multi-device use, switch to ~15
  minutes + refresh tokens (see `docs/MOBILE_EVOLUTION.md`).
- Bcrypt for password hashing.
- The token is stored in `localStorage` on the web — acceptable for a
  personal app, but on a multi-user product, prefer `httpOnly` cookies with
  SameSite=Lax to mitigate XSS.

## 6. UUIDs everywhere

Primary keys are UUIDs, not integers. Slight storage cost in exchange for:

- No sequence reservation contention.
- Safe to expose in URLs without leaking row counts.
- Easy to generate client-side later (useful for offline-first mobile).

## 7. Money as `Numeric(12, 2)`, dates as `DATE`

Never floats for money. Never datetime for "what day was this expense" —
that invites timezone bugs (an expense on May 1st 23:00 in Lisbon
becoming April 30th when sent to a UTC-stored API).

## 8. Categories: global, slug-based

Categories are seeded globally rather than per-user. The slug
(`food`, `transport`, …) is the stable identifier the LLM and any external
clients reason about; the display name and emoji are presentation. If
per-user custom categories are needed later, add a nullable
`user_id` foreign key and treat `NULL` as "system category".

## 9. Tailwind, no UI framework

Tailwind handles styling. No shadcn/ui, no Material, no Chakra. The app has
about a dozen elements and the design is editorial-specific — bringing in
a kit would dilute the aesthetic and add weight.

## 10. Editorial aesthetic, not "dashboardy"

Most expense apps look like accounting software. This one looks like a
notebook: serif display font, warm paper background, monospace amounts,
minimal chrome. Personal apps should feel personal.
