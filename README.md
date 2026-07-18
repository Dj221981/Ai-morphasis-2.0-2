# Ai-morphasis-2.0-2

Ai-morphasis-2.0-2 is a Python FastAPI service with supporting AI model configuration code under `src/`.
This repository currently ships a runnable API, lightweight health/readiness checks, and a test suite that validates the supported service surface.

## Repository layout

- `app/main.py` - FastAPI application entrypoint and routes.
- `src/config/model_config.py` - model configuration registry used by the API.
- `src/models/` and `src/data/` - neural network and preprocessing modules.
- `tests/` - API and configuration tests executed in CI.
- `.github/workflows/tests.yml` - required CI workflow for syntax + tests.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest tests -q
```

## Optional ML dependency set

If you need to execute TensorFlow-based modules in `src/models` and `src/data`, install:

```bash
pip install -r requirements-ml.txt
```

## Environment variables

- `APP_ENV` - used by `/ready` to report readiness (`ready` vs `degraded`).

## Current production-readiness scope

This repository now provides:
- a runnable FastAPI app with basic hardening headers and global error handling,
- coherent CI in `.github/workflows/tests.yml`,
- dependencies and docs aligned to the tested runtime path.

Remaining work for full production readiness would include auth, persistent storage, structured observability, and deployment infrastructure.
