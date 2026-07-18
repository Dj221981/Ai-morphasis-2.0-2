# ============================================================
# Stage 1 — build / dependency resolution
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools required for some compiled wheels.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ============================================================
# Stage 2 — runtime image
# ============================================================
FROM python:3.11-slim AS runtime

# Run as a non-root user for security.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy pre-built site-packages from builder stage.
COPY --from=builder /install /usr/local

# Copy application source.
COPY app/ app/
COPY src/ src/

# Give ownership to the non-root user.
RUN chown -R appuser:appuser /app

USER appuser

# Expose the default uvicorn port.
EXPOSE 8000

# ============================================================
# Healthcheck — Kubernetes / Docker will poll /health
# ============================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# ============================================================
# Entrypoint
# ============================================================
# Uses uvicorn in production mode: no --reload, multiple workers.
# Override CMD at deploy time to tune worker count, host, port, etc.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
