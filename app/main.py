"""
Ai-morphasis 2.0-2 FastAPI application.

Production baseline: liveness/readiness probes, security headers,
global exception handling, CORS, rate limiting, structured logging,
and configuration metadata endpoint.
"""

import logging
import os
import warnings
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger.json import JsonFormatter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config.model_config import get_config, list_configs
from src.config.settings import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """
    Configure root logger.

    In staging/production the root handler emits newline-delimited JSON so
    that log-aggregation stacks (Loki, CloudWatch, Datadog, …) can parse
    structured fields without regex.  In development plain text is used for
    readability.
    """
    handler = logging.StreamHandler()

    if settings.json_logs:
        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        )
        handler.setFormatter(formatter)
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    logging.basicConfig(
        level=settings.log_level,
        handlers=[handler],
        force=True,
    )


_configure_logging()
logger = logging.getLogger(__name__)

if settings.is_production and settings.cors_origins == "*":
    warnings.warn(
        "CORS_ORIGINS is set to '*' in production. "
        "Set it to a comma-separated list of allowed origins.",
        RuntimeWarning,
        stacklevel=1,
    )

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Ai-morphasis-2.0-2",
    version="2.0.2",
    description="AI agent training and orchestration service",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", summary="Service root")
@limiter.limit(settings.rate_limit)
def root(request: Request) -> dict[str, str]:
    """Return a brief service description."""
    return {"service": "Ai-morphasis-2.0-2", "version": "2.0.2"}


@app.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """
    Liveness probe — indicates the process is running.

    Returns HTTP 200 as long as the application process is alive.
    This endpoint does **not** check downstream dependencies and is
    intentionally excluded from rate limiting so that orchestrators
    (Kubernetes, ECS, etc.) can poll it freely.
    """
    return {"status": "ok"}


@app.get("/ready", summary="Startup readiness check")
def ready() -> JSONResponse:
    """
    Startup readiness check.

    Verifies that critical runtime configuration is available and valid
    before the service is considered ready to accept traffic.  Currently checks:

    - ``APP_ENV`` environment variable is set to a recognised value
      (``development``, ``staging``, or ``production``).

    Returns HTTP 200 when ready, HTTP 503 when not.

    .. note::
        This is a *startup* readiness check, not a full dependency probe.
        It does not verify database connectivity, model weights, or
        downstream service availability.
    """
    valid_envs = {"development", "staging", "production"}
    app_env = os.getenv("APP_ENV", "").strip()

    issues: list[str] = []
    if not app_env:
        issues.append("APP_ENV is not set")
    elif app_env not in valid_envs:
        issues.append(f"APP_ENV='{app_env}' is not a recognised value; expected one of {sorted(valid_envs)}")

    if issues:
        logger.warning("Readiness check failed: %s", "; ".join(issues))
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "issues": issues,
                "note": (
                    "Set APP_ENV to 'development', 'staging', or 'production' "
                    "before sending traffic. See .env.example for guidance."
                ),
            },
        )

    return JSONResponse(status_code=200, content={"status": "ready", "env": app_env})


@app.get("/configs", summary="List available model configurations")
@limiter.limit(settings.rate_limit)
def configs(request: Request) -> dict[str, Any]:
    """
    Return the names and top-level structure of all registered model configurations.

    Configurations are defined in ``src/config/model_config.py`` and cover
    DQN, policy gradient, small, large, continuous, and multi-agent setups.
    """
    names = list_configs()
    return {
        "configs": {name: get_config(name) for name in names},
        "available": names,
    }

