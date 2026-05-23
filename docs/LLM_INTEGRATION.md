# LLM Integration Guide

This document describes how to evolve the current scaffold into a working
chatbot / natural-language interface, without rewriting the API.

## What's already in place

- `app/llm/registry.py` — a provider-agnostic `Tool` dataclass with built-in
  converters to OpenAI and Anthropic tool schemas.
- `app/llm/tools/` — two tool handlers already wired:
  - `search_expenses` (filtered query, reuses `expense_service.list_expenses`)
  - `add_expense` (reuses `expense_service.create_expense`)
- `REGISTRY` dict in `app/llm/tools/__init__.py` — single place to add tools.

The tool handlers are **regular Python functions** that take an authenticated
`(session, user_id, validated_input)` triple. They are unit-testable without
any LLM involvement.

## Why this shape

A common failure mode for LLM features is letting the model bypass business
rules — for example, fetching expenses by injecting a different `user_id` into
a SQL string. We avoid that entirely:

- The LLM never sees raw SQL.
- `user_id` is injected by the *caller*, not by the model. The model emits
  filter parameters; the caller adds the authenticated user.
- All tool inputs are validated by Pydantic before they reach the database.

## Adding a chat endpoint (when you're ready)

1. **Pick a provider.** The simplest is Anthropic's Messages API with tools.
   Anthropic API key already has a slot in `core/config.py`.

2. **Create `app/llm/providers/anthropic_provider.py`** with one function:

   ```python
   async def chat(session, user_id, conversation: list[Message]) -> Message:
       client = AsyncAnthropic(api_key=settings.anthropic_api_key)
       tools = [t.to_anthropic_schema() for t in REGISTRY.values()]
       # Loop: send messages + tools → if model returns tool_use, dispatch
       # to REGISTRY[name].handler(session, user_id, input_model(**args))
       # → append tool_result and continue, until model returns plain text.
   ```

3. **Create `app/api/v1/endpoints/chat.py`** with a single POST endpoint that
   takes the conversation history and current user (via `CurrentUser`), then
   calls the provider.

4. **Mount it** in `app/api/v1/router.py`.

5. **Add a chat panel** to the frontend (a sidebar `<Drawer />` with a text
   input is enough to start). It POSTs to `/api/v1/chat` and renders the
   reply. The same panel will work in the mobile app.

## Adding a new tool

1. Create `app/llm/tools/my_tool.py` with:
   - a Pydantic input model
   - a handler `def my_tool(session, user_id, payload) -> dict:`
2. Register it in `app/llm/tools/__init__.py`:
   ```python
   REGISTRY["my_tool"] = Tool(
       name="my_tool",
       description="What it does, written for the model.",
       input_model=MyToolInput,
       handler=my_tool,
   )
   ```
3. The next chat call will see it automatically.

## Tool ideas worth adding next

- `summarize_month(month: str)` — total + breakdown by category. Useful for
  prompts like "how did I do in April?".
- `top_categories(date_from, date_to, limit)` — leaderboard. Reuses the same
  filter engine.
- `delete_expense(expense_id)` — only after `search_expenses` confirms the
  match, to avoid the model deleting the wrong row.

## Cost and latency tips

- Tool definitions add to the prompt on every turn. Trim descriptions, and
  consider lazy-registering tools per endpoint when the registry grows.
- Cache `REGISTRY[...].to_anthropic_schema()` results — schemas don't change
  per request.
- For "summary" tools, return aggregates in the tool result rather than
  letting the model loop over individual rows.
