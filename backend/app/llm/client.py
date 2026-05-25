"""OpenAI-compatible LLM client.

A single `AsyncOpenAI` instance is reused across requests. The `base_url`,
`api_key` and `model` come from settings — defaults target a local Ollama
daemon, but pointing at OpenAI is just an env-var change.
"""

from openai import AsyncOpenAI

from app.core.config import get_settings

_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        s = get_settings()
        _client = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key)
    return _client
