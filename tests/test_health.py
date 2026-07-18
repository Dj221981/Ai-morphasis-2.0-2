"""Tests for the FastAPI application endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Ai-morphasis-2.0-2"
    assert "version" in body


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_security_headers() -> None:
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_ready_without_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert any("APP_ENV" in issue for issue in body["issues"])


def test_ready_with_invalid_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "not_a_valid_env")
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"


def test_ready_with_invalid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    response = client.get("/ready")
    # "test" is not a recognised value — expect 503
    assert response.status_code == 503


def test_ready_with_valid_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["env"] == "production"


def test_configs_endpoint() -> None:
    response = client.get("/configs")
    assert response.status_code == 200
    body = response.json()
    assert "available" in body
    assert "configs" in body
    assert "dqn" in body["available"]
    assert isinstance(body["configs"]["dqn"], dict)


def test_not_found_returns_404() -> None:
    response = client.get("/nonexistent-route")
    assert response.status_code == 404


def test_health_xss_protection_header() -> None:
    response = client.get("/health")
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"


def test_ready_with_staging_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["env"] == "staging"


def test_ready_failure_body_has_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert "note" in body
    assert "APP_ENV" in body["note"]


def test_configs_all_names_returned() -> None:
    response = client.get("/configs")
    body = response.json()
    expected = {"dqn", "policy", "small", "large", "continuous", "multi_agent"}
    assert expected == set(body["available"])


def test_root_version_value() -> None:
    response = client.get("/")
    assert response.json()["version"] == "2.0.2"
