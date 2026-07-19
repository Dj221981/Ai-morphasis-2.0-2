# Ai-morphasis 2.0-2

Ai-morphasis 2.0-2 is a Python project that combines:

- A FastAPI service (`app/main.py`)
- Agent and model logic in `src/`
- A comprehensive pytest suite in `tests/`

## Requirements

- Python 3.9+
- pip

## Installation

```bash
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:

- `GET /` - service banner
- `GET /health` - liveness
- `GET /ready` - readiness

## Test and Lint

```bash
pytest tests -v
python -m flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Project Structure

- `app/` - FastAPI application entrypoint
- `src/` - core data, agent, config, and model modules
- `tests/` - unit and behavior tests
- `docs/` - API and repository documentation
- `agents/cerribro/` - cerribro profile configuration and docs

## Documentation

- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRIBUTING.md`
- `Software.md`

## License

This project is licensed under the MIT License. See `LICENSE`.
