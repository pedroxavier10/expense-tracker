"""Chat endpoint: streaming tool-calling loop against an OpenAI-compatible LLM.

The endpoint emits Server-Sent Events. Each event is a single line:

    data: {"type": "...", ...}\\n\\n

Event types
-----------
- text          {"delta": "<chunk>"}             text token appended to the reply
- tool_use      {"name": "...", "args": {...}}   model decided to call a tool
- tool_result   {"name": "...", "ok": bool}      tool finished (success or failure)
- client_action {"action": "...", "payload": …}  frontend should perform a UI action
- done          {}                                end of response
- error         {"message": "..."}                fatal error; followed by `done`
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.llm.client import get_llm_client
from app.llm.tools import REGISTRY
from app.models.category import Category
from app.schemas.chat import ChatRequest
from app.services.category_service import list_categories as fetch_categories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


SYSTEM_PROMPT_TEMPLATE = """You are the assistant of a personal expense tracker.
Today is {today} (UTC). The user's locale is pt-PT — answer in European Portuguese.
Format money as e.g. "12,50 €". Be concise.

Available expense categories (use these exact ids):
{categories}

You have access to tools that read and modify the user's expenses. Use them
whenever they would give a more accurate answer than guessing.

Rules:
- When the user wants to register an expense, pick the best-matching category
  from the list above based on the expense description (e.g. "lanche",
  "supermercado" → food; "gasolina", "uber" → transport). Only ask the user
  to choose if the description gives no hint at all.
- Once you have amount, expense_date, description and category_id, call
  `add_expense` directly — do NOT open the form.
- Only call `open_add_expense_form` when a field other than category_id is
  missing or ambiguous (e.g. the amount is unclear). Pass whatever you inferred.
- You CANNOT delete expenses. If the user asks to delete one, do NOT call
  any tool for that purpose — instead, tell them they can do it in the
  "Despesas" page (suggest they filter by the description or date you found).
- For statistics ("how much in April?", "where did I spend most?"), use
  `monthly_summary` or `top_categories`.
- Never fabricate expense ids or category ids.
"""


def _build_system_prompt(categories: list[Category]) -> str:
    categories_text = "\n".join(
        f"  - {c.slug} (id: {c.id}): {c.name} {c.icon or ''}"
        for c in categories
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=datetime.now(UTC).date().isoformat(),
        categories=categories_text,
    )


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _run_tool(
    session: Session, user_id: UUID, name: str, raw_args: str
) -> tuple[dict, dict | None]:
    """Execute a tool. Returns (tool_result_dict, optional_client_action)."""
    tool = REGISTRY.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}, None
    try:
        args = json.loads(raw_args or "{}") or {}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON arguments: {exc}"}, None
    try:
        validated = tool.input_model(**args)
    except ValidationError as exc:
        return {"error": "Validation error", "details": exc.errors()}, None
    try:
        result = tool.handler(session, user_id, validated)
    except Exception as exc:  # noqa: BLE001 — surface as tool error to the model
        logger.exception("Tool %s failed", name)
        return {"error": str(exc)}, None

    client_action: dict | None = None
    if isinstance(result, dict) and "action" in result:
        client_action = {
            "action": result["action"],
            "payload": {k: v for k, v in result.items() if k != "action"},
        }
    return result, client_action


async def _stream_chat(session: Session, user_id: UUID, request: ChatRequest) -> AsyncIterator[str]:
    settings = get_settings()
    client = get_llm_client()

    categories = fetch_categories(session)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt(categories)},
        *[{"role": m.role.value, "content": m.content} for m in request.messages],
    ]
    tools_schema = [t.to_openai_schema() for t in REGISTRY.values()]

    logger.info(
        "Chat started — model: %s | history: %d messages | tools available: %s",
        settings.llm_model,
        len(request.messages),
        [t["function"]["name"] for t in tools_schema],
    )

    try:
        for iteration in range(settings.llm_max_tool_iterations):
            logger.debug(
                "Iteration %d/%d — calling LLM", iteration + 1, settings.llm_max_tool_iterations
            )

            stream = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                tools=tools_schema,
                temperature=settings.llm_temperature,
                stream=True,
            )

            accumulated_text = ""
            tool_calls: dict[int, dict[str, Any]] = {}
            finish_reason: str | None = None

            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    accumulated_text += delta.content
                    yield _sse({"type": "text", "delta": delta.content})

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        slot = tool_calls.setdefault(idx, {"id": None, "name": "", "arguments": ""})
                        if tc.id:
                            slot["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                slot["name"] += tc.function.name
                            if tc.function.arguments:
                                slot["arguments"] += tc.function.arguments

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

            if not tool_calls:
                logger.info(
                    "Chat done — finished after %d iteration(s), no tool calls", iteration + 1
                )
                yield _sse({"type": "done"})
                return

            logger.info(
                "Iteration %d — model requested %d tool(s): %s",
                iteration + 1,
                len(tool_calls),
                [tc["name"] for tc in tool_calls.values()],
            )

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": accumulated_text or None,
                "tool_calls": [
                    {
                        "id": tc["id"] or f"call_{idx}",
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"] or "{}"},
                    }
                    for idx, tc in sorted(tool_calls.items())
                ],
            }
            messages.append(assistant_msg)

            dispatched_client_action = False
            for idx, tc in sorted(tool_calls.items()):
                name = tc["name"]
                try:
                    args_preview = json.loads(tc["arguments"] or "{}")
                except json.JSONDecodeError:
                    args_preview = tc["arguments"]

                logger.debug("Calling tool %r with args: %s", name, args_preview)
                yield _sse({"type": "tool_use", "name": name, "args": args_preview})

                result, client_action = await _run_tool(session, user_id, name, tc["arguments"])
                ok = isinstance(result, dict) and "error" not in result
                logger.info("Tool %r → %s | result: %s", name, "OK" if ok else "ERROR", result)
                yield _sse({"type": "tool_result", "name": name, "ok": ok})
                if client_action is not None:
                    yield _sse({"type": "client_action", **client_action})
                    dispatched_client_action = True

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"] or f"call_{idx}",
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

            if dispatched_client_action:
                logger.info(
                    "Chat done — client_action dispatched, handing control back to the user"
                )
                yield _sse({"type": "done"})
                return

            if finish_reason == "stop":
                logger.info("Chat done — model signalled stop after %d iteration(s)", iteration + 1)
                yield _sse({"type": "done"})
                return

        logger.warning(
            "Chat aborted — reached max tool iterations (%d) without a final answer",
            settings.llm_max_tool_iterations,
        )
        yield _sse(
            {
                "type": "error",
                "message": "Reached max tool iterations without a final answer.",
            }
        )
        yield _sse({"type": "done"})

    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat stream failed")
        yield _sse({"type": "error", "message": str(exc)})
        yield _sse({"type": "done"})


@router.post("/stream", summary="Stream a chat reply (SSE)")
async def stream_chat(
    payload: ChatRequest, session: SessionDep, current_user: CurrentUser
) -> StreamingResponse:
    return StreamingResponse(
        _stream_chat(session, current_user.id, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
