import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(title="Ai-morphasis-2.0-2")
STARTED_AT = datetime.now(timezone.utc)


def _parse_csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


allowed_hosts = _parse_csv_env("APP_ALLOWED_HOSTS", "*")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware("http")
async def add_response_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "no-referrer"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Ai-morphasis 2.0-2 API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ok"}
