"""Application configuration loaded from environment variables.

Uses pydantic-settings to provide typed, validated configuration. All settings
are loaded from environment variables or a `.env` file at the project root.
"""

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET_KEY = "insecure-development-key-change-me"


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
    secret_key: str = Field(default=INSECURE_DEFAULT_SECRET_KEY)
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    algorithm: str = "HS256"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Authentication
    # Google sign-in is the only login method in production. Defaults to on so a
    # forgotten variable can never expose the passwordless dev login.
    google_auth_enabled: bool = True
    google_client_id: str | None = None
    # Comma-separated list of emails allowed to sign in with Google. Empty = nobody.
    allowed_emails: str = ""
    # User the dev login signs in as when google_auth_enabled is false.
    dev_user_email: str = "me@example.com"

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

    # --- Recurring-expense suggestions ---
    # Distinct months an expense (same description, category and ~amount) must
    # appear in before the app suggests turning it into a recurring rule.
    recurring_suggestion_min_months: int = Field(default=3, ge=2, le=12)

    @model_validator(mode="after")
    def _check_production_safety(self) -> Self:
        if self.google_auth_enabled and not self.google_client_id:
            raise ValueError("GOOGLE_CLIENT_ID is required when GOOGLE_AUTH_ENABLED is true")
        if self.environment.lower() == "production":
            if not self.google_auth_enabled:
                raise ValueError("GOOGLE_AUTH_ENABLED must be true in production")
            if self.secret_key == INSECURE_DEFAULT_SECRET_KEY:
                raise ValueError("SECRET_KEY must be set in production")
        return self

    @property
    def allowed_emails_set(self) -> set[str]:
        """Parse comma-separated allowed emails into a lowercase set."""
        return {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}

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
