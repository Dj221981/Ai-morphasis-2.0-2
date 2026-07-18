from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Ai-morphasis 2.0-2 API is running"}


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api", "version": "0.1.0"}


def test_ready_endpoint_degraded_without_required_environment_variables(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "detail": "Missing environment variables: APP_ENV",
    }


def test_ready_endpoint_ready_when_required_environment_variables_present(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "detail": "All runtime checks passed"}


def test_configs_endpoint() -> None:
    response = client.get("/configs")

    assert response.status_code == 200
    payload = response.json()
    assert "available_configs" in payload
    assert "dqn" in payload["available_configs"]


def test_security_headers_present() -> None:
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
