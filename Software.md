# Software

## Overview

Ai-morphasis 2.0-2 is a FastAPI service providing a runtime baseline for AI agent training configuration and orchestration.

## Purpose

The service exposes a versioned REST API for:
- health and readiness probing
- retrieving model training configurations

ML model training modules (`src/models/`, `src/data/`, `src/agents/`) are scaffolded in the repository but are not yet connected to the API surface. They require optional dependencies (TensorFlow, NumPy) that are not included in the default `requirements.txt`.

## Features

- FastAPI REST API with liveness and readiness probes
- Security headers on every response
- Global exception handler
- Model configuration registry accessible via API
- pytest test suite with CI on Python 3.10 / 3.11 / 3.12

## Getting Started

### Prerequisites

- Python 3.10 or later
- `pip`

### Installation

```bash
git clone https://github.com/Dj221981/Ai-morphasis-2.0-2.git
cd Ai-morphasis-2.0-2
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set APP_ENV=development
```

### Running the Software

```bash
uvicorn app.main:app --reload
```

The service starts on `http://127.0.0.1:8000` by default.

### Running Tests

```bash
APP_ENV=development python -m pytest tests -v
```

## Usage

See [docs/API.md](docs/API.md) for the full API reference.

Quick check:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}

curl http://127.0.0.1:8000/ready
# {"status":"ready","env":"development"}   (requires APP_ENV to be set)

curl http://127.0.0.1:8000/configs | python -m json.tool
```

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit as needed.

Key variable:

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | **Yes** | Runtime environment (`development`, `staging`, `production`). Used by the `/ready` probe. |
| `LOG_LEVEL` | No | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO`. |

## Project Structure

```
app/main.py              FastAPI application entry point
src/config/              Model configuration registry (importable, fully tested)
src/models/              TensorFlow neural network models (optional)
src/data/                Data preprocessing utilities (optional)
src/agents/              Agent orchestration scaffold (optional)
tests/                   pytest test suite
.github/workflows/       CI (tests.yml = canonical; django.yml = disabled)
requirements.txt         Runtime + test dependencies
.env.example             Environment variable template
```

## Contributing

1. Create a branch for your changes.
2. Make your updates and add tests.
3. Run `APP_ENV=development python -m pytest tests -v` to verify.
4. Open a pull request targeting `main`.

## What is not yet production ready

- ML modules not wired to API — TensorFlow is an optional dependency; install separately for ML use.
- No authentication — add an API-key or OAuth2 layer if the service is exposed externally.
- No distributed tracing or metrics endpoint.
- No deployment contract (Dockerfile, process definition).
- No observability stack (metrics, tracing).
- `/ready` only checks env-var presence; extend for full dependency checks.

## License

See repository root for license information.

