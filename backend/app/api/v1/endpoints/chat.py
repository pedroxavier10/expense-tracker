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
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


SYSTEM_PROMPT_TEMPLATE = """You are the assistant of a personal expense tracker.
Today is {today} (UTC). The user's locale is pt-PT — answer in European Portuguese.
Format money as e.g. "12,50 €". Be concise.

You have access to tools that read and modify the user's expenses. Use them
whenever they would give a more accurate answer than guessing. Prefer calling
`list_categories` before `add_expense` if you don't already know the category id.

Rules:
- To register an expense with all required fields known (amount, date,
  description, category_id), call `add_expense`.
- If any required field is missing or ambiguous, call `open_add_expense_form`
  with the values you do have — the UI will open a form prefilled for the
  user to confirm. Do NOT invent missing values.
- You CANNOT delete expenses. If the user asks to delete one, do NOT call
  any tool for that purpose — instead, tell them they can do it in the
  "Despesas" page (suggest they filter by the description or date you found).
- For statistics ("how much in April?", "where did I spend most?"), use
  `monthly_summary` or `top_categories`.
- Never fabricate expense ids or category ids.
"""


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(today=datetime.now(UTC).date().isoformat())


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
        args = json.loads(raw_args or "{}")
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


async def _stream_chat(
    session: Session, user_id: UUID, request: ChatRequest
) -> AsyncIterator[str]:
    settings = get_settings()
    client = get_llm_client()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt()},
        *[{"role": m.role.value, "content": m.content} for m in request.messages],
    ]
    tools_schema = [t.to_openai_schema() for t in REGISTRY.values()]

    try:
        for _ in range(settings.llm_max_tool_iterations):
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
                        slot = tool_calls.setdefault(
                            idx, {"id": None, "name": "", "arguments": ""}
                        )
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
                yield _sse({"type": "done"})
                return

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

            for idx, tc in sorted(tool_calls.items()):
                name = tc["name"]
                try:
                    args_preview = json.loads(tc["arguments"] or "{}")
                except json.JSONDecodeError:
                    args_preview = tc["arguments"]
                yield _sse({"type": "tool_use", "name": name, "args": args_preview})

                result, client_action = await _run_tool(
                    session, user_id, name, tc["arguments"]
                )
                ok = isinstance(result, dict) and "error" not in result
                yield _sse({"type": "tool_result", "name": name, "ok": ok})
                if client_action is not None:
                    yield _sse({"type": "client_action", **client_action})

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"] or f"call_{idx}",
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

            if finish_reason == "stop":
                yield _sse({"type": "done"})
                return

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
