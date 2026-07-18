# Ai-morphasis 2.0-2

A FastAPI service providing a runtime baseline for AI agent training configuration and orchestration.

## Current status

**Production-ready baseline** — the API service is fully containerised, CI-wired, rate-limited, CORS-configured, and emits structured JSON logs in staging/production.  All configuration is validated via pydantic-settings.  The ML model training modules (`src/models/`, `src/data/`, `src/agents/`) are scaffolded but not yet connected to the API surface and are not covered by default CI (they require optional heavy dependencies like TensorFlow).

## Repository layout

```
app/          FastAPI application (entry point)
src/
  config/     Model configuration registry + pydantic-settings (importable, tested)
  models/     TensorFlow neural network models (optional, not wired to API)
  data/       Data preprocessing utilities (optional)
  agents/     Agent orchestration scaffold (optional)
tests/        pytest test suite (covers app/, src/config/, and production features)
Dockerfile    Multi-stage production container image
docker-compose.yml  Local development convenience
workflows/    Legacy non-functional workflow file (do not use; see .github/workflows/)
.github/
  workflows/
    tests.yml     Canonical CI — lint + pytest on Python 3.10/3.11/3.12
    django.yml    Disabled (this repo does not use Django)
```

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/Dj221981/Ai-morphasis-2.0-2.git
cd Ai-morphasis-2.0-2
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and set APP_ENV=development (required for /ready probe)

# 3. Run the service (local Python)
uvicorn app.main:app --reload

# 3b. Run the service (Docker)
docker compose up --build

# 4. Run tests
APP_ENV=development python -m pytest tests -v
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Liveness probe — always 200 if process is alive |
| GET | `/ready` | Startup readiness check — 200 when `APP_ENV` is set, 503 otherwise |
| GET | `/configs` | List and return all registered model configurations |

### `/ready` semantics

`/ready` checks that the `APP_ENV` environment variable is set. This is a *startup* readiness check, not a full dependency probe. It does **not** verify database connectivity, model weights, or downstream service availability. If you need a richer readiness check, extend the `ready()` function in `app/main.py`.

## CI

CI runs on every push and pull request to `main` via `.github/workflows/tests.yml`:

- **lint** — `flake8` syntax and undefined-name checks (hard failure)
- **test** — `pytest` on Python 3.10, 3.11, and 3.12 (hard failure)

No checks are hidden with `|| true`.

## What is not yet production ready

The following gaps remain before calling this fully production ready:

- **No auth** — the API is open; add authentication (e.g. API-key header, OAuth2) if exposed externally.
- **ML modules not wired to API** — `src/models/`, `src/data/`, and `src/agents/` are scaffolded but not integrated into the FastAPI service.
- **TensorFlow not in requirements** — `src/models/neural_network.py` requires TensorFlow which is an optional dependency; it must be installed separately for ML use.
- **No observability** — no distributed tracing (OpenTelemetry) or metrics (Prometheus) endpoint; add these for production monitoring.
- **Shallow readiness probe** — `/ready` only checks env-var presence; extend it for real dependency checks (database, model weights, downstream services).
- **No database** — the service is stateless; add a persistence layer if required.

## Configuration

See `.env.example` for all supported environment variables.

Model configurations are managed in `src/config/model_config.py` and accessible via the `/configs` API endpoint.

