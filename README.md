# Ai-morphasis 2.0-2

A FastAPI service providing a runtime baseline for AI agent training configuration and orchestration.

## Current status

**Production-baseline ready** — core API service is runnable, CI is wired, and the configuration registry is stable. The ML model training modules (`src/models/`, `src/data/`, `src/agents/`) are scaffolded but not yet connected to the API surface and are not covered by default CI (they require optional heavy dependencies like TensorFlow).

## Repository layout

```
app/          FastAPI application (entry point)
src/
  config/     Model configuration registry (importable, tested)
  models/     TensorFlow neural network models (optional, not wired to API)
  data/       Data preprocessing utilities (optional)
  agents/     Agent orchestration scaffold (optional)
tests/        pytest test suite (covers app/ and src/config/)
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

# 3. Run the service
uvicorn app.main:app --reload

# 4. Run tests
APP_ENV=test python -m pytest tests -v
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

Even with this baseline, the following gaps remain before calling this fully production ready:

- **No auth / rate limiting** — the API is open; add authentication if exposed externally.
- **ML modules not wired to API** — `src/models/`, `src/data/`, and `src/agents/` are scaffolded but not integrated into the FastAPI service.
- **TensorFlow not in requirements** — `src/models/neural_network.py` requires TensorFlow which is an optional dependency; it must be installed separately for ML use.
- **No deployment contract** — no Dockerfile or production process definition is included.
- **No observability** — no metrics, tracing, or structured log output contract beyond basic logging.
- **Shallow readiness probe** — `/ready` only checks env-var presence; extend it for real dependency checks.
- **No database** — the service is stateless; add persistence layer if required.

## Configuration

See `.env.example` for all supported environment variables.

Model configurations are managed in `src/config/model_config.py` and accessible via the `/configs` API endpoint.

