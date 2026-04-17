"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings sourced from environment variables.

    Required secrets will raise ValidationError on startup if not set.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram (required)
    telegram_bot_token: str = Field(..., description="Bot token from BotFather")

    # Anthropic (required)
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Claude model identifier"
    )

    # Miro (required)
    miro_access_token: str = Field(..., description="Miro developer access token")
    miro_board_id: str = Field(..., description="Target Miro board ID")

    # Storage
    storage_root: str = Field(default="./data", description="Root directory for file storage")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/glucotrack.db",
        description="SQLAlchemy async connection string",
    )

    # Session settings
    session_idle_threshold_minutes: int = Field(
        default=30, description="Minutes of inactivity before disambiguation prompt (FR-013)"
    )
    session_idle_expiry_hours: int = Field(
        default=24, description="Hours before abandoned session auto-expires (FR-012)"
    )
    session_disambiguate_timeout_hours: int = Field(
        default=2,
        description="Hours to wait for disambiguation response before auto-closing (FR-013)",
    )

    # Rate limits — Constitution VII cost guard
    ai_max_calls_per_user_per_day: int = Field(
        default=10, description="Max AI analysis calls per user per day"
    )
    ai_max_tokens_per_session: int = Field(
        default=4000, description="Max Claude output tokens per session analysis"
    )

    @field_validator(
        "telegram_bot_token", "anthropic_api_key", "miro_access_token", "miro_board_id"
    )
    @classmethod
    def not_empty(cls, v: str, info: object) -> str:
        if not v or v.strip() == "":
            raise ValueError("must not be empty")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Call once at startup."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
