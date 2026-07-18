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
    assert "APP_ENV" in body["missing_env"]


def test_ready_with_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


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
