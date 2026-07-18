"""
Tests for the FastAPI application endpoints, authentication, rate limiting, and security headers.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import APP_VERSION, create_app
from app.settings import Settings, get_settings

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_client(extra_env: dict | None = None) -> TestClient:
    """Build a TestClient with specific settings overrides.

    Keys in *extra_env* must match the Settings field names (lowercase).
    Example: ``{"api_key": "secret"}``
    """
    env = {"app_env": "development", **(extra_env or {})}
    settings = Settings(**env)

    test_app = create_app(settings=settings)
    # Override get_settings so all FastAPI dependencies use the test settings.
    test_app.dependency_overrides[get_settings] = lambda: settings

    return TestClient(test_app)


# Default client — auth disabled (no API_KEY set)
client = _make_client()


# ── Root / Health / Ready ─────────────────────────────────────────────────────


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Ai-morphasis 2.0-2 API is running"}


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api", "version": APP_VERSION}


def test_ready_endpoint_returns_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


# ── Security headers ──────────────────────────────────────────────────────────


def test_security_headers_present() -> None:
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


# ── /configs endpoint ─────────────────────────────────────────────────────────


def test_configs_endpoint_without_auth_disabled() -> None:
    """When API_KEY is not set, /configs is accessible without a key."""
    response = client.get("/configs")
    assert response.status_code == 200
    payload = response.json()
    assert "available_configs" in payload
    assert "dqn" in payload["available_configs"]


def test_configs_endpoint_requires_key_when_auth_enabled() -> None:
    """When API_KEY is set, /configs returns 401 without the key."""
    auth_client = _make_client({"api_key": "secret-key-123"})
    response = auth_client.get("/configs")
    assert response.status_code == 401


def test_configs_endpoint_accepts_correct_key_when_auth_enabled() -> None:
    """When API_KEY is set, /configs returns 200 with the correct key."""
    auth_client = _make_client({"api_key": "secret-key-123"})
    response = auth_client.get("/configs", headers={"X-API-Key": "secret-key-123"})
    assert response.status_code == 200
    assert "available_configs" in response.json()


def test_configs_endpoint_rejects_wrong_key() -> None:
    """When API_KEY is set, /configs returns 401 with a wrong key."""
    auth_client = _make_client({"api_key": "secret-key-123"})
    response = auth_client.get("/configs", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


# ── Settings validation ────────────────────────────────────────────────────────


def test_settings_rejects_invalid_app_env() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(app_env="invalid_env")


def test_settings_rejects_invalid_log_level() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(app_env="development", log_level="VERBOSE")


def test_settings_normalizes_app_env_to_lowercase() -> None:
    s = Settings(app_env="Production")
    assert s.app_env == "production"


