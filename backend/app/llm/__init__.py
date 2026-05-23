"""LLM integration module (scaffold).

This module is intentionally minimal right now. It defines the *shape* the
future LLM layer will take so that adding a chatbot endpoint later is purely
additive — no refactoring of the rest of the codebase.

## Design

The LLM layer follows the **tool-calling** pattern (OpenAI function calling,
Anthropic tools, etc.):

    user prompt
        │
        ▼
    LLM provider  ──►  picks one of our registered tools
        │
        ▼
    tool function  ──►  calls into `app.services.*`  (the same business logic
        │                the REST API uses, so behaviour stays consistent)
        ▼
    structured result  ──►  LLM phrases the natural-language answer

Every tool is:

1. Defined as a pure Python function in `app/llm/tools/`.
2. Annotated with a Pydantic input model (auto-generates the JSON schema the
   LLM provider needs).
3. Registered in `registry.py`.

Adding a new capability for the LLM = adding one file to `tools/` and one
line to the registry.

## Security note

Tools never accept a `user_id` from the LLM — it's always injected by the
caller from the authenticated session. The LLM cannot fabricate a user to
query someone else's data.

## When to actually implement

Implement when you want any of:

- natural-language search ("how much did I spend on food last month?")
- prompt-driven expense entry ("add 12€ lunch yesterday")
- monthly summaries / insights

See `docs/LLM_INTEGRATION.md` for the step-by-step rollout plan.
"""
