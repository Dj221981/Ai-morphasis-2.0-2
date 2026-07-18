# API Reference

FastAPI application entrypoint: `app/main.py`
Settings module: `app/settings.py`

## Endpoints

### `GET /`
Returns service identity. No authentication required.

```json
{"message": "Ai-morphasis 2.0-2 API is running"}
```

### `GET /health`
Liveness probe. No authentication required. Always returns 200 when the process is alive.

```json
{"status": "ok", "service": "api", "version": "0.2.0"}
```

### `GET /ready`
Readiness probe. No authentication required.

Returns `ready` when all required environment variables are set and valid.
Returns `degraded` with a detail message when required variables are missing.

```json
{"status": "ready", "detail": "All runtime checks passed"}
```

### `GET /configs`
Returns available model configuration presets from `src/config/model_config.py`.

**Authentication:** required when `API_KEY` env var is set — pass value in `X-API-Key` header.

**Rate limited:** 60 requests/minute per IP by default (configurable via `RATE_LIMIT` env var).

```json
{"available_configs": ["dqn", "policy", "small", "large", "continuous", "multi_agent"]}
```

---

## Authentication

When `API_KEY` is configured, protected endpoints require the `X-API-Key` request header.

| Condition | Response |
|-----------|----------|
| No key set (empty `API_KEY`) | Auth disabled, all requests allowed |
| Correct key in header | `200 OK` |
| Missing or wrong key | `401 Unauthorized` |

---

## Rate limiting

Protected endpoints are rate limited per client IP using slowapi.

| Condition | Response |
|-----------|----------|
| Under limit | Normal response |
| Limit exceeded | `429 Too Many Requests` |

---

## Error handling

| Condition | Status | Body |
|-----------|--------|------|
| Auth failure | `401` | `{"detail": "Invalid or missing API key."}` |
| Rate limit exceeded | `429` | `{"detail": "Rate limit exceeded. Please slow down."}` |
| Unhandled exception | `500` | `{"detail": "Internal server error"}` |

---

## Security headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Cache-Control: no-store`

---

## Configuration reference

See `app/settings.py` for the full Settings model and `docs/` for additional guides.

## Testing

```bash
APP_ENV=development python -m pytest tests -q
```

