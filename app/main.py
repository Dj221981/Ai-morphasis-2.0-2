from __future__ import annotations

import logging
import logging.config

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from limits.storage import MemoryStorage
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.settings import Settings, get_settings
from src.config.model_config import list_configs

APP_VERSION = "0.2.0"

# ── Logging ───────────────────────────────────────────────────────────────────


def configure_logging(log_level: str = "INFO") -> None:
    """Set up structured JSON logging for the entire process."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.json.JsonFormatter",
                    "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["console"], "level": log_level},
        }
    )


LOGGER = logging.getLogger("ai_morphasis_api")

# ── Rate limiter ──────────────────────────────────────────────────────────────


def _get_rate_limit_key(request: Request) -> str:
    """Return a per-client identifier for rate limiting (client IP address)."""
    return request.client.host if request.client else "unknown"


_limiter = Limiter(key_func=_get_rate_limit_key, storage_uri="memory://")

# ── Auth ──────────────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    api_key: str | None = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency that enforces API key auth when configured."""
    if not settings.api_key:
        # Auth disabled — allow all traffic (development mode)
        return
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# ── Response models ───────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ── App factory ───────────────────────────────────────────────────────────────


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    configure_logging(resolved.log_level)
    LOGGER.info(
        "Starting Ai-morphasis API",
        extra={"version": APP_VERSION, "env": resolved.app_env},
    )

    app = FastAPI(
        title="Ai-morphasis-2.0-2",
        version=APP_VERSION,
        description="FastAPI service for Ai-morphasis-2.0-2.",
        docs_url="/docs" if resolved.app_env != "production" else None,
        redoc_url="/redoc" if resolved.app_env != "production" else None,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    app.state.limiter = _limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        LOGGER.warning("Rate limit exceeded", extra={"path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please slow down."},
        )

    # ── Security headers ───────────────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    # ── Request logging ────────────────────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        response = await call_next(request)
        LOGGER.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
        return response

    # ── Global exception handler ───────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("Unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ── Public endpoints (no auth, no rate-limit) ──────────────────────────────

    @app.get("/", response_model=MessageResponse, tags=["meta"])
    def root() -> MessageResponse:
        return MessageResponse(message="Ai-morphasis 2.0-2 API is running")

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="api", version=APP_VERSION)

    @app.get("/ready", tags=["meta"])
    def ready(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        if not settings.app_env:
            return {"status": "degraded", "detail": "APP_ENV not configured"}
        return {"status": "ready", "detail": "All runtime checks passed"}

    # ── Protected endpoints ────────────────────────────────────────────────────

    @app.get(
        "/configs",
        tags=["model"],
        dependencies=[Depends(require_api_key)],
    )
    @_limiter.limit(resolved.rate_limit)
    def configs(request: Request) -> dict[str, list[str]]:
        return {"available_configs": list_configs()}

    return app


app = create_app()

