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

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, SessionDep
from app.schemas.chat import ChatRequest
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream", summary="Stream a chat reply (SSE)")
async def stream_chat(
    payload: ChatRequest, session: SessionDep, current_user: CurrentUser
) -> StreamingResponse:
    return StreamingResponse(
        chat_service.stream_chat(
            session, current_user.id, payload, language=current_user.language
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
