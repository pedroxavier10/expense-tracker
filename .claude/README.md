# `.claude/` — Project-Local Agents and Skills

These are scoped helpers for Claude Code / Claude.ai when working on this
project. They encode the project's conventions so additions stay consistent
across sessions.

## Skills (`skills/`)

Skills are auto-loaded by Claude when relevant. They describe *how* to do
recurring tasks in this codebase.

- **`expense-domain`** — adding endpoints, services, models, and LLM tools
  to the backend with the right layering.
- **`api-integration`** — adding frontend features that call the API,
  keeping types and the client consistent.

## Agents (`agents/`)

Agents are focused sub-task experts you can invoke explicitly.

- **`migration-author`** — produces Alembic migrations after model
  changes, including a careful review of the autogenerate output.
- **`llm-tool-author`** — adds a new tool to `app/llm/tools/` with input
  schema, handler, registry entry, and a unit test.

## When to add more

Add a skill when you find yourself explaining the same convention twice.
Add an agent when a task has a multi-step recipe that benefits from
isolation (separate context, tighter tool scope).
