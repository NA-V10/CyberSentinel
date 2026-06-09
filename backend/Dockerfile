FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------
LABEL maintainer="CyberSentinel AI"
LABEL description="CyberSentinel AI — FastAPI backend with LangGraph agents"
LABEL version="1.0.0"

WORKDIR /app

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
# gcc         — compiling C extensions (e.g. psycopg2, cryptography)
# libpq-dev   — PostgreSQL client library headers (asyncpg / psycopg2)
# curl        — used by the HEALTHCHECK below
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python dependencies — separate layer for cache efficiency
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Application source
# ---------------------------------------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Runtime directories
# ---------------------------------------------------------------------------
# /app/models  — persisted ML model artefacts (mounted as a named volume)
# /app/logs    — application logs
# /app/data    — sample data / uploads (host-mounted in compose)
RUN mkdir -p /app/models /app/logs /app/data

# ---------------------------------------------------------------------------
# Non-root user for security
# ---------------------------------------------------------------------------
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser \
    && chown -R appuser:appgroup /app

USER appuser

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
EXPOSE 8000

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
# In production swap --reload for --workers 4 (or use gunicorn + uvicorn worker)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
