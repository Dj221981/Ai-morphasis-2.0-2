# Changelog

All notable changes to Ai-morphasis-2.0-2 are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-07-18

### Added
- **Settings validation at startup** — pydantic-settings enforces `APP_ENV`
  (must be `development`, `staging`, or `production`) and `LOG_LEVEL` on process start; the app refuses to boot if required values are invalid or missing.
- **API key authentication** — `X-API-Key` header enforced on protected endpoints
  when `API_KEY` env var is set. Public endpoints (`/`, `/health`, `/ready`) are always reachable. Set `API_KEY` to an empty string (default) to disable auth in development.
- **Rate limiting** — slowapi enforces a configurable per-IP limit (default `60/minute`) on protected endpoints. Returns HTTP 429 when exceeded.
- **Structured JSON logging** — all log output is formatted as JSON via `python-json-logger`. Each HTTP request is logged with method, path, and status code.
- **Dockerfile** (multi-stage) — builds a minimal `python:3.12-slim` runtime image running as a non-root user with a built-in HEALTHCHECK.
- **docker-compose.yml** — single-service compose file for local development and deployment.
- **`/configs` endpoint moved to protected scope** — requires `X-API-Key` when `API_KEY` is configured.
- **`app/settings.py`** — new Settings module, single source of truth for all runtime configuration.

### Changed
- App version bumped from `0.1.0` to `0.2.0`.
- OpenAPI docs (`/docs`, `/redoc`) are disabled in `production` environment.
- `requirements.txt` extended with `pydantic-settings`, `slowapi`, `python-json-logger`.
- `.env.example` updated to document all required and optional variables.

### Fixed
- `src/config/model_config.py`: `get_config()` now returns a deep copy to prevent mutation of shared config state.

---

## [0.1.0] — 2026-07-17

### Added
- FastAPI service scaffold with `/`, `/health`, `/ready`, `/configs` endpoints.
- Security response headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control`).
- Global exception handler returning structured 500 responses.
- `pytest` test suite covering health/readiness endpoints and security headers.
- GitHub Actions CI workflow at `.github/workflows/tests.yml` with required checks (no `|| true` masking) on Python 3.11 and 3.12.
- Workflow `permissions: { contents: read }` hardening.
- `requirements.txt` with pinned dependencies.
- `requirements-ml.txt` for optional TensorFlow stack.
- Replaced profile-style `README.md` with project-specific docs.
- Replaced placeholder `Software.md` with install/run/test instructions.
- Corrected `docs/API.md` to match implemented endpoints.
- Fixed invalid Python literals (`true`/`false`) in `src/config/model_config.py`.

---
