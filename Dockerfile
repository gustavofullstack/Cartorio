# syntax=docker/dockerfile:1.7
# ============================================
# Cartorio Backend - Multi-stage Dockerfile
# Build context: REPO ROOT (Easypanel uses this path)
# Docker image is built with:
#   docker buildx build -f Dockerfile -t easypanel/cartorio/api .
# So all COPY paths are RELATIVE TO REPO ROOT.
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
# pyproject.toml + uv.lock live in backend/ (subdir of repo root)
COPY backend/pyproject.toml backend/uv.lock ./

# Install deps into a virtual env
RUN uv sync --frozen --no-install-project --no-dev

# Now copy project source and install the project itself
# mcp_server.py lives in backend/ root (not backend/app/), so copy whole backend
COPY backend/app ./app
COPY backend/mcp_server.py ./mcp_server.py
COPY backend/pyproject.toml ./
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

# Copy virtual env + app + mcp_server from builder
COPY --from=builder --chown=cartorio:cartorio /build/.venv /app/.venv
COPY --from=builder --chown=cartorio:cartorio /build/app /app/app
COPY --from=builder --chown=cartorio:cartorio /build/mcp_server.py /app/mcp_server.py

# Fix shebangs: uv generates absolute paths like /build/.venv/bin/python
# which DON'T exist in the runtime stage. Rewrite to /app/.venv/bin/python.
RUN sed -i 's|#!/build|#!/app|g' /app/.venv/bin/* && \
    sed -i 's|/build/.venv/bin/python|/app/.venv/bin/python|g' /app/.venv/bin/*

USER cartorio

EXPOSE 8000

# Health check (uses /health endpoint, no curl needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        r = urllib.request.urlopen('http://localhost:8000/health', timeout=3); \
        sys.exit(0 if r.status == 200 else 1)"

# Default: 1 worker for MVP. Scale via Easypanel replicas for prod.
# Note: app lifespan calls Base.metadata.create_all() to auto-create
# tables on first start (idempotent). Alembic migrations can replace
# this later.
# Sleep 30s before start to give the cartorio-network-monitor.sh
# script time to connect this container to cartorio_supabase_default
# (Swarm removes the bridge network on restart; monitor reconnects it).
CMD ["sh", "-c", "sleep 30 && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
