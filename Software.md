# Software Overview

## Purpose

This repository provides a FastAPI service for Ai-morphasis-2.0-2 with supporting model configuration modules.

## Requirements

- Python 3.11+
- Docker (optional, for container deployment)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional ML stack (TensorFlow):

```bash
pip install -r requirements-ml.txt
```

## Configure

Copy `.env.example` to `.env` and set at minimum:

```bash
cp .env.example .env
# Required: APP_ENV=development | staging | production
# Optional: API_KEY=<secret> to enable endpoint authentication
```

## Run

```bash
APP_ENV=development uvicorn app.main:app --reload
```

Or with Docker Compose:

```bash
docker compose up --build
```

## Test

```bash
APP_ENV=development python -m pytest tests -q
```

## Configuration

All settings are in `app/settings.py` and loaded from environment variables.
See `.env.example` for a full reference.

Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | ✅ | `development`, `staging`, or `production` |
| `API_KEY` | No | Enables `X-API-Key` authentication when non-empty |
| `LOG_LEVEL` | No | Log verbosity (`INFO` default) |
| `RATE_LIMIT` | No | Rate limit for protected endpoints (`60/minute` default) |

## CI

GitHub Actions required test workflow: `.github/workflows/tests.yml`

Runs syntax validation and the pytest suite on Python 3.11 and 3.12.

## Release

Changes are documented in `CHANGELOG.md` using the Keep a Changelog format.
