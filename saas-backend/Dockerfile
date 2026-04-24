# syntax=docker/dockerfile:1
# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.runtime.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

RUN mkdir -p ${PLAYWRIGHT_BROWSERS_PATH} \
    && python -m playwright install chromium \
    && chmod -R 755 ${PLAYWRIGHT_BROWSERS_PATH}

# Copy source code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD sh -c "if [ \"${APP_RUNTIME:-}\" = \"worker\" ] || [ \"${RAILWAY_SERVICE_NAME:-}\" = \"ai-gym-os-worker\" ] || [ \"${ENABLE_SCHEDULER:-false}\" = \"true\" ]; then exit 0; else python -c \"import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health/ready')\"; fi" || exit 1

CMD ["sh", "-c", "if [ \"${APP_RUNTIME:-}\" = \"worker\" ] || [ \"${RAILWAY_SERVICE_NAME:-}\" = \"ai-gym-os-worker\" ] || [ \"${ENABLE_SCHEDULER:-false}\" = \"true\" ]; then python -m app.worker; else uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2; fi"]
