# API Reference

## Base service

FastAPI application entrypoint: `app/main.py`

## Endpoints

### `GET /`
Returns service identity.

Example response:

```json
{
  "message": "Ai-morphasis 2.0-2 API is running"
}
```

### `GET /health`
Liveness endpoint for basic process health.

Example response:

```json
{
  "status": "ok",
  "service": "api",
  "version": "0.1.0"
}
```

### `GET /ready`
Readiness endpoint based on required runtime environment.

- Returns `ready` when required environment variables are present.
- Returns `degraded` with details when required variables are missing.

Example degraded response:

```json
{
  "status": "degraded",
  "detail": "Missing environment variables: APP_ENV"
}
```

### `GET /configs`
Returns available model configuration keys from `src/config/model_config.py`.

Example response:

```json
{
  "available_configs": ["dqn", "policy", "small", "large", "continuous", "multi_agent"]
}
```

## Error handling

Unhandled exceptions are converted to:

```json
{
  "detail": "Internal server error"
}
```

with HTTP 500 status.

## Security headers

The app adds basic hardening headers to responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Cache-Control: no-store`

## Testing

Run API and config tests:

```bash
pytest tests -q
```
