"""LLM tool registry.

Each tool is described once here. Provider-specific schema generators (OpenAI,
Anthropic, Gemini) consume this registry to expose the tools to their
respective APIs.

This file deliberately contains *definitions only* — no actual LLM calls yet.
The handler functions live in `app/llm/tools/` and call into `app.services.*`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

# Result key for a UI action that should run *alongside* the conversation (the
# model keeps answering), unlike a top-level `"action"` key, which hands control
# back to the user and ends the turn. The chat loop strips it from the result
# the model sees and forwards it to the client as a `client_action` event.
FOLLOWUP_ACTION_KEY = "followup_action"


@dataclass
class Tool:
    """A single tool exposed to the LLM."""

    name: str
    description: str
    input_model: type[BaseModel]
    # Handler signature: (session, user_id, validated_input) -> JSON-serializable result
    handler: Callable[..., Any]

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }

    def to_anthropic_schema(self) -> dict:
        """Convert to Anthropic tools format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


# The registry is populated lazily in `tools/__init__.py` to avoid import cycles.
# `from app.llm.tools import REGISTRY` is the canonical access point.
