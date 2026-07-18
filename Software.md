# Software Overview

## Purpose

This repository provides a FastAPI service for Ai-morphasis-2.0-2 with supporting model configuration modules.
The currently supported path is: install dependencies, run the API from `app/main.py`, and validate with pytest.

## Requirements

- Python 3.11+
- `pip`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional ML stack for TensorFlow modules:

```bash
pip install -r requirements-ml.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest tests -q
```

## Configuration

- `APP_ENV` controls `/ready` status reporting.
- Model presets are defined in `src/config/model_config.py` and exposed at `GET /configs`.

## CI

GitHub Actions required test workflow:
- `.github/workflows/tests.yml`

It performs syntax validation and runs the pytest suite on Python 3.11 and 3.12.
