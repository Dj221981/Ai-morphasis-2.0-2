from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config.model_config import list_configs

LOGGER = logging.getLogger("ai_morphasis_api")
APP_VERSION = "0.1.0"


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ai-morphasis-2.0-2",
        version=APP_VERSION,
        description="FastAPI service for Ai-morphasis-2.0-2.",
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    @app.get("/", response_model=MessageResponse)
    def root() -> MessageResponse:
        return MessageResponse(message="Ai-morphasis 2.0-2 API is running")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="api", version=APP_VERSION)

    @app.get("/ready")
    def ready() -> dict[str, str]:
        required_env_vars = ("APP_ENV",)
        missing = [key for key in required_env_vars if not os.getenv(key)]
        if missing:
            return {
                "status": "degraded",
                "detail": f"Missing environment variables: {', '.join(missing)}",
            }
        return {"status": "ready", "detail": "All runtime checks passed"}

    @app.get("/configs")
    def configs() -> dict[str, list[str]]:
        return {"available_configs": list_configs()}

    return app


app = create_app()
