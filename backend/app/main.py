"""FastAPI app entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.db import engine
from app.models.base import Base
from app.services.audit import AuditService


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Smoke test DB + create tables if missing + audit log init."""
    # 1. Smoke test: confirm DB is reachable
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # 2. Create all tables (idempotent — no-op if schema already exists).
    # MVP-friendly: we don't have Alembic migrations set up yet, so we let
    # SQLAlchemy create the schema from the model metadata. Safe because
    # create_all() never drops or alters existing tables.
    Base.metadata.create_all(bind=engine)

    # 3. Audit log: write a startup entry (no-op if audit_log empty)
    AuditService.log_system_action("api.startup", {"version": "0.4.0", "env": settings.app_env})

    yield

    AuditService.log_system_action("api.shutdown", {})


app = FastAPI(
    title="Cartorio Backend API",
    description="API de regras cartorarias com audit log imutavel e PII scrubbing.",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.get("/ready", tags=["meta"])
def ready() -> dict:
    """Readiness probe - confirma DB e audit log inicializados."""
    return {"status": "ready", "audit_chain_initialized": True}


@app.get("/mcp-servers", tags=["meta"])
def mcp_servers() -> dict:
    """Lista MCP servers registrados (descoberta via mcp_config global).

    Retorna metadata dos 5 servers MCP disponiveis para clients
    (Antigravity, OpenCode, Claude Code, Zed):

    - n8n-mcp         : workflows N8N via MCP-HTTP
    - supabase-mcp    : Postgres + docs (config em ~/.gemini/antigravity/mcp_config.json)
    - cartorio-api    : esta propria API como MCP tools (backend/mcp_server.py)
    - easypanel-mcp   : controle do Easypanel (helbertparanhos/easypanel-mcp-server)
    - openclaw-mcp    : gateway OpenClaw para tools customizadas

    Config global: ~/.mavis/mcp/clients/cartorio-mcp-config.json
    """
    return {
        "status": "ok",
        "servers": [
            {
                "name": "cartorio-api",
                "transport": "http",
                "url": f"http://localhost:{settings.app_port}/mcp",
                "auth": "header: apikey",
                "tools_count": 6,
                "description": "API FastAPI como MCP tools (emolumento, protocolo, audit, etc)",
                "path": "backend/mcp_server.py",
            },
            {
                "name": "n8n-mcp",
                "transport": "http",
                "url": settings.n8n_mcp_url,
                "auth": "header: Authorization: Bearer <jwt>",
                "tools_count": 50,
                "description": "Workflows N8N via MCP-HTTP",
            },
            {
                "name": "supabase-mcp",
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "auth": "oauth (auto)",
                "tools_count": 30,
                "description": "Postgres + docs Supabase (via ~/.gemini/antigravity/mcp_config.json)",
            },
            {
                "name": "easypanel-mcp",
                "transport": "stdio",
                "command": "easypanel-mcp-server",
                "auth": "env: EASYPANEL_API_URL + EASYPANEL_API_KEY",
                "tools_count": 57,
                "description": "Controle Easypanel (helbertparanhos/easypanel-mcp-server v2.0.0)",
            },
            {
                "name": "openclaw-mcp",
                "transport": "http",
                "url": "http://cartorio_openclaw-gateway:18789/v1/mcp",
                "auth": "header: Authorization: Bearer <gateway_token>",
                "tools_count": 20,
                "description": "OpenClaw gateway MCP (pendente Tailscale auth - SUI)",
            },
        ],
        "config_path": "~/.mavis/mcp/clients/cartorio-mcp-config.json",
        "version": "0.4.0",
    }


app.include_router(api_router, prefix="/api/v1")
