FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --prefix=/install -r /app/requirements.txt

FROM tensorflow/tensorflow:2.15.0 AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    MODEL_PATH=/models/latest
RUN useradd -m -u 10001 appuser
COPY --from=builder /install /usr/local
COPY . /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready')" || exit 1
CMD ["python", "-m", "src.agents.super_agentic_agents"]
