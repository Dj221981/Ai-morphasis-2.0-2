# Architecture Guide

## Overview

Ai-morphasis 2.0-2 is organized into a lightweight API layer and modular core logic under `src/`.

## Main Components

### API Layer

- **Path:** `app/main.py`
- **Responsibilities:**
  - Expose HTTP endpoints (`/`, `/health`, `/ready`)
  - Apply host and security middleware
  - Return safe 500 responses with request IDs

### Core Logic

- **Path:** `src/`
- **Modules:**
  - `src/agents/` - agent orchestration and task execution behavior
  - `src/models/` - neural network and model-related logic
  - `src/data/` - preprocessing utilities
  - `src/config/` - model/runtime configuration definitions

### Test Suite

- **Path:** `tests/`
- **Responsibilities:**
  - Validate API behavior
  - Validate agent, task, and memory systems
  - Validate model and configuration logic

## Runtime Flow

1. Client calls FastAPI endpoint.
2. Middleware adds request ID and security headers.
3. Route handler returns status/result.
4. Internal modules in `src/` provide computational and orchestration behavior.

## Quality and Validation

- Tests: `pytest tests -v`
- Lint (critical): `python -m flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics`

