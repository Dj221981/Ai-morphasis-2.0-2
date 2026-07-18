"""
Application settings validated at startup using pydantic-settings.

All settings are loaded from environment variables (or a .env file).
The app will refuse to start if required values are missing or invalid.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required ──────────────────────────────────────────────────────────────
    app_env: str = Field(
        ...,
        description="Deployment environment. Must be 'development', 'staging', or 'production'.",
    )

    # ── Authentication ─────────────────────────────────────────────────────────
    api_key: str = Field(
        default="",
        description=(
            "API key for X-API-Key header authentication. "
            "Set to a non-empty string to enable auth. "
            "Leave empty to disable authentication (development only)."
        ),
    )

    # ── Application ────────────────────────────────────────────────────────────
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ── Rate limiting ──────────────────────────────────────────────────────────
    rate_limit: str = Field(
        default="60/minute",
        description="Default rate limit applied to protected endpoints (slowapi format).",
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        if value.lower() not in allowed:
            raise ValueError(
                f"app_env must be one of {sorted(allowed)}, got '{value}'."
            )
        return value.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got '{value}'.")
        return upper


def get_settings() -> Settings:
    """Return validated settings (evaluated once per process)."""
    return Settings()
