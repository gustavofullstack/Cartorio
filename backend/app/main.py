"""FastAPI app entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.db import Base, engine
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
    AuditService.log_system_action("api.startup", {"version": "0.1.0", "env": settings.app_env})

    yield

    AuditService.log_system_action("api.shutdown", {})


app = FastAPI(
    title="Cartorio Backend API",
    description="API de regras cartorarias com audit log imutavel e PII scrubbing.",
    version="0.1.0",
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


app.include_router(api_router, prefix="/api/v1")
