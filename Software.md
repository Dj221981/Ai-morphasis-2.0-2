# Software

## Overview

This document describes the software in this repository and provides a quick reference for setup, execution, and contribution.

## Purpose

The goal of the software is to provide a clear, maintainable foundation for the Ai-morphasis 2.0-2 project, including API delivery and agent/model experimentation.

## Features

- FastAPI service with health and readiness endpoints
- Core modules for data preprocessing, model configuration, neural network logic, and agent orchestration
- Comprehensive pytest coverage across API, agents, tasking, memory, and model behavior
- GitHub Actions workflows for CI and quality checks

## Getting Started

### Prerequisites

- Python 3.9 or newer
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Running the Software

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

Typical usage flows:

1. Start the API service and verify health:
   - `GET /health`
   - `GET /ready`
2. Run tests during development:
   - `pytest tests -v`
3. Run critical lint checks:
   - `python -m flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics`

## Configuration

Key environment variables:

- `APP_ALLOWED_HOSTS` (comma-separated list, defaults to `*`)
- `x-request-id` request header (optional, generated if absent)

## Project Structure

- `app/main.py` - FastAPI application and middleware
- `src/agents/super_agentic_agents.py` - agent orchestration and execution
- `src/models/neural_network.py` - model implementation logic
- `src/data/preprocessing.py` - data preparation utilities
- `src/config/model_config.py` - model/runtime configuration
- `tests/` - automated tests
- `docs/` - API, architecture, and contribution docs

## Contributing

1. Create a branch for your changes.
2. Make your updates.
3. Test your changes.
4. Open a pull request.

## License

MIT License (see `LICENSE`).
