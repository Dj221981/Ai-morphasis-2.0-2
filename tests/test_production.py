"""Tests for production-readiness additions: CORS, rate limiting, settings."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.config.settings import Settings

client = TestClient(app)


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


def test_cors_header_present_for_allowed_origin() -> None:
    """An Origin matching the allow-list receives Access-Control-Allow-Origin."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # When CORS_ORIGINS includes '*' or the specific origin, the header is set.
    assert "access-control-allow-origin" in response.headers


def test_cors_preflight_returns_200() -> None:
    """OPTIONS preflight requests are handled without a 404/405."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_settings_default_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings default to development when APP_ENV is not set."""
    monkeypatch.delenv("APP_ENV", raising=False)
    s = Settings()
    assert s.app_env == "development"


def test_settings_production_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    s = Settings()
    assert s.app_env == "production"
    assert s.is_production is True


def test_settings_invalid_app_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "invalid_env")
    with pytest.raises(Exception):
        Settings()


def test_settings_cors_origins_list_single() -> None:
    s = Settings(app_env="development", cors_origins="http://example.com")
    assert s.cors_origins_list == ["http://example.com"]


def test_settings_cors_origins_list_multiple() -> None:
    s = Settings(
        app_env="development",
        cors_origins="http://example.com, https://app.example.com",
    )
    assert "http://example.com" in s.cors_origins_list
    assert "https://app.example.com" in s.cors_origins_list


def test_settings_json_logs_in_production() -> None:
    s = Settings(app_env="production")
    assert s.json_logs is True


def test_settings_no_json_logs_in_development() -> None:
    s = Settings(app_env="development")
    assert s.json_logs is False


def test_settings_json_logs_in_staging() -> None:
    s = Settings(app_env="staging")
    assert s.json_logs is True
