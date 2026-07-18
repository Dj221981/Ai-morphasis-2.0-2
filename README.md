# Ai-morphasis-2.0-2

Ai-morphasis-2.0-2 is a Python FastAPI service with supporting AI model configuration code under `src/`.

## Repository layout

```
app/
  main.py          FastAPI application (routes, middleware, auth, rate limiting)
  settings.py      Validated settings loaded from environment on startup
src/
  config/          Model configuration registry
  models/          Neural network modules (TensorFlow — optional)
  data/            Data preprocessing utilities (TensorFlow — optional)
  agents/          Agent orchestration code
tests/             API and configuration unit tests
Dockerfile         Multi-stage Docker build (non-root runtime)
docker-compose.yml Local development / deployment compose file
requirements.txt   Runtime dependencies (no TensorFlow)
requirements-ml.txt  Optional TensorFlow stack
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy and configure the environment file:

```bash
cp .env.example .env
# Set APP_ENV=development (required)
# Optionally set API_KEY=<your-key> to enable authentication
```

Run the API:

```bash
APP_ENV=development uvicorn app.main:app --reload
```

Run tests:

```bash
APP_ENV=development python -m pytest tests -q
```

## Docker

Build and run with Docker Compose:

```bash
cp .env.example .env   # edit .env with your values
docker compose up --build
```

The API is available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs` (disabled in `production`).

## Configuration

All settings are loaded from environment variables or a `.env` file. The app **refuses to start** if required values are invalid.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | ✅ | — | `development`, `staging`, or `production` |
| `API_KEY` | No | `""` | X-API-Key for protected endpoints. Empty = auth disabled |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `RATE_LIMIT` | No | `60/minute` | Rate limit for protected endpoints (slowapi format) |

See `.env.example` for a full reference.

## Authentication

Set `API_KEY` to a non-empty secret to enable authentication on protected endpoints. Pass the key as an `X-API-Key` header. Public endpoints (`/`, `/health`, `/ready`) are always accessible.

```bash
# Generate a key
openssl rand -hex 32

# Use in requests
curl -H "X-API-Key: <your-key>" http://localhost:8000/configs
```

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | No | Service identity |
| `GET` | `/health` | No | Liveness probe |
| `GET` | `/ready` | No | Readiness probe |
| `GET` | `/configs` | When `API_KEY` set | Available model configuration presets |

See `docs/API.md` for full endpoint reference.

## Optional ML dependency set

`src/models/` and `src/data/` require TensorFlow. Install:

```bash
pip install -r requirements-ml.txt
```

## CI

GitHub Actions workflow runs syntax validation and tests on Python 3.11 and 3.12:
- `.github/workflows/tests.yml`

