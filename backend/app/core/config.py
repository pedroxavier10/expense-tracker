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
        default="postgresql+psycopg://expense_user:expense_pass@localhost:5432/expense_tracker"
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

    # LLM providers (optional, used by future llm module)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

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
