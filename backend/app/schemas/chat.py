"""Chat request/response schemas.

The backend is stateless: the frontend always sends the full conversation
history; the response stream contributes a single new assistant turn.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ChatRole(StrEnum):
    user = "user"
    assistant = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=0, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
