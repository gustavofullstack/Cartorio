# syntax=docker/dockerfile:1.7
# ============================================
# Cartorio Backend - Multi-stage Dockerfile
# ============================================
# Stage 1: builder (uv sync --frozen)
# Stage 2: runtime (slim Python 3.12)
# ============================================

FROM python:3.12-slim AS builder

# Disable bytecode + buffer for cleaner Docker layers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv==0.5.11

WORKDIR /build

# Copy dependency manifests FIRST (better layer caching)
COPY pyproject.toml uv.lock ./

# Install deps into a virtual env (copy out to runtime stage)
RUN uv sync --frozen --no-install-project --no-dev

# Now copy project source and install the project itself
COPY app ./app
RUN uv sync --frozen --no-dev


# ============================================
# Stage 2: runtime
# ============================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Runtime user (no root in container)
RUN groupadd -r cartorio && useradd -r -g cartorio cartorio

WORKDIR /app

# Copy virtual env + app from builder
COPY --from=builder --chown=cartorio:cartorio /build/.venv /app/.venv
COPY --from=builder --chown=cartorio:cartorio /build/app /app/app

USER cartorio

EXPOSE 8000

# Health check (uses /health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        r = urllib.request.urlopen('http://localhost:8000/health', timeout=3); \
        sys.exit(0 if r.status == 200 else 1)"

# Default: 1 worker for MVP. Scale via Easypanel replicas for prod.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
