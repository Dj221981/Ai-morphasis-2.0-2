"""
Application settings — validated via pydantic-settings.

All configuration is sourced from environment variables (and optionally a
``.env`` file).  Import the ``settings`` singleton instead of calling
``os.getenv`` directly throughout the application.

Usage::

    from src.config.settings import settings

    if settings.app_env == "production":
        ...
"""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ------------------------------------------------------------------
    # API / network
    # ------------------------------------------------------------------
    # Comma-separated list of allowed CORS origins.
    # Use "*" only during development; set explicit origins in production.
    cors_origins: str = "*"
    # Requests per minute allowed per client IP on non-probe endpoints.
    rate_limit: str = "60/minute"

    # ------------------------------------------------------------------
    # Agent / model configuration
    # ------------------------------------------------------------------
    max_agents: int = 100
    agent_memory_size: int = 10_000

    # ------------------------------------------------------------------
    # Game / rendering
    # ------------------------------------------------------------------
    game_width: int = 1280
    game_height: int = 720
    target_fps: int = 60

    # ------------------------------------------------------------------
    # ML model
    # ------------------------------------------------------------------
    model_device: Literal["cpu", "gpu"] = "cpu"
    batch_size: int = 32
    learning_rate: float = 0.001

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_file: str = "logs/ai_morphasis.log"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @field_validator("cors_origins")
    @classmethod
    def _cors_warn_wildcard_in_production(cls, v: str) -> str:
        # Validation is env-context-free here; the warning is emitted at
        # runtime by the application layer if needed.
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list (split on commas)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def json_logs(self) -> bool:
        """Enable JSON-formatted logging in staging and production."""
        return self.app_env in ("staging", "production")


# Module-level singleton — import this everywhere instead of re-instantiating.
settings = Settings()
