# API Reference

## HTTP Endpoints

All endpoints return JSON. Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`) are added to every response.

---

### `GET /`

**Service root** — returns the service name and version.

**Response 200**

```json
{"service": "Ai-morphasis-2.0-2", "version": "2.0.2"}
```

---

### `GET /health`

**Liveness probe** — indicates the process is running.

Returns HTTP 200 as long as the application process is alive. Does **not** check downstream dependencies.

**Response 200**

```json
{"status": "ok"}
```

---

### `GET /ready`

**Startup readiness check** — verifies that critical runtime configuration is present.

Currently checks that `APP_ENV` is set. Returns HTTP 200 when ready, HTTP 503 when not.

> **Note:** This is a *startup* readiness check, not a full dependency probe. It does not verify database connectivity, model weights, or downstream service availability. Extend the `ready()` function in `app/main.py` to add deeper checks.

**Response 200 — ready**

```json
{"status": "ready", "env": "development"}
```

**Response 503 — not ready**

```json
{
  "status": "not_ready",
  "issues": ["APP_ENV is not set"],
  "note": "Set APP_ENV to 'development', 'staging', or 'production' before sending traffic. See .env.example for guidance."
}
```

---

### `GET /configs`

**Model configurations** — returns all registered model training configurations.

Configurations are defined in `src/config/model_config.py` and cover DQN, policy gradient, small, large, continuous, and multi-agent setups.

**Response 200**

```json
{
  "available": ["dqn", "policy", "small", "large", "continuous", "multi_agent"],
  "configs": {
    "dqn": { "model": {...}, "environment": {...}, "training": {...}, ... },
    ...
  }
}
```

---

## Error responses

Unhandled server errors return HTTP 500:

```json
{"error": "internal_server_error", "detail": "An unexpected error occurred."}
```

---

## Configuration module

`src/config/model_config` exposes two public functions:

```python
from src.config.model_config import get_config, list_configs

# List available configuration names
names = list_configs()  # ['dqn', 'policy', 'small', 'large', 'continuous', 'multi_agent']

# Get a deep copy of a named configuration
cfg = get_config("dqn")  # raises ValueError for unknown names
```

---

## Modules not yet in API surface

The following modules exist in the repository but are **not connected to the API** and are not covered by default CI. They require optional dependencies (TensorFlow, NumPy):

- `src/models/neural_network.py` — DQN and policy gradient neural network models
- `src/data/preprocessing.py` — Data normalisation and augmentation utilities
- `src/agents/super_agentic_agents.py` — Agent orchestration scaffold

---

## Logging

The application uses Python's built-in `logging` module. Set the `LOG_LEVEL` environment variable to control verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default is `INFO`.

---

**For more information, see:**
- [Software.md](../Software.md)
- [README.md](../README.md)

