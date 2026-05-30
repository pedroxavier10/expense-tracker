"""Application configuration loaded from environment variables.

Uses pydantic-settings to provide typed, validated configuration. All settings
are loaded from environment variables or a `.env` file at the project root.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values are loaded from environment variables. See `.env.example` for the
    full list of available configuration options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Expense Tracker API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://expense_user:expense_pass@localhost:5466/expense_tracker"
    )

    # Security
    secret_key: str = Field(default="insecure-development-key-change-me")
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    algorithm: str = "HS256"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Default user (bootstrapped on first run for single-user personal use)
    default_user_email: str = "me@example.com"
    default_user_password: str = "changeme"

    # LLM
    # Defaults target a local Ollama daemon (OpenAI-compatible API).
    # To switch to OpenAI: set llm_base_url=https://api.openai.com/v1, set llm_api_key
    # to a real key, and llm_model to e.g. "gpt-4o-mini".
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"  # ignored by Ollama; required by the OpenAI client
    llm_model: str = "llama3.2"
    # Model for short utility tasks (e.g. generating a category slug). Falls
    # back to llm_model when unset; can point at a small/fast model such as
    # Groq's "llama-3.1-8b-instant".
    llm_utility_model: str | None = None
    llm_temperature: float = 0.2
    llm_max_tool_iterations: int = 6  # safety limit on the tool-calling loop

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance.

    Using lru_cache ensures we only parse environment variables once per process,
    which is important because Settings() reads from disk.
    """
    return Settings()
