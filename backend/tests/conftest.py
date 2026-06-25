"""Test fixtures."""

import os
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test env BEFORE importing app modules.
# Sprint 4 S01: usa setdefault para permitir override via env var
# (CI/prod tem DATABASE_URL=postgresql; dev local pode usar sqlite).
# Se a env var ja esta setada (Postgres), respeita.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)  # 64 chars hex equivalente pra teste
# .env local pode ter CHATWOOT_ACCOUNT_ID/INBOX_ID vazios (placeholders nao parseados
# como int). Forca valores numericos via env vars, que tem precedencia sobre .env.
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
# A15: Forca defaults canonicos de pool mesmo se .env local tiver valores
# antigos (10/5). Settings.precedence = .env < env var, entao setdefault aqui
# sobrescreve o .env mas NAO conflita com override explicito em CI.
os.environ.setdefault("DB_POOL_SIZE", "20")
os.environ.setdefault("DB_MAX_OVERFLOW", "10")
os.environ.setdefault("DB_POOL_RECYCLE", "3600")
os.environ.setdefault("DB_POOL_TIMEOUT", "30")
os.environ.setdefault("DB_POOL_PRE_PING", "true")
# API key usada pelos testes que batem em endpoints protegidos por X-API-Key
# (ex: DELETE /cliente/{id}, GET /cliente/{id}/historico). Setada aqui pra
# estar disponivel antes de app.config criar o singleton `settings` na import.
# Deve ter EXATAMENTE 64 chars (validacao strict em config.py: B0.3 2026-06-25).
# Gerada via `openssl rand -hex 32` — valor fixo pra reprodutibilidade dos testes.
TEST_CARTORIO_API_KEY = "a" * 64  # 64 chars hex equivalente pra teste
os.environ.setdefault("CARTORIO_API_KEY", TEST_CARTORIO_API_KEY)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.models.base import Base  # noqa: E402

# Importa modelos concretos para que Base.metadata esteja populado nos testes
# (caso contrario tabelas nao existem no SQLite in-memory e lifespan da app
#  falha em AuditService.log_system_action → "no such table: audit_log")
from app.models import (  # noqa: E402,F401
    audit_log,  # usado por AuditService.log_system_action no lifespan
    cliente,
    protocolo,
    atendimento,
    documento,
    conversa,
    outbox_message,
    webhook_event,
)


@pytest.fixture
def db_session(monkeypatch) -> Iterator[Session]:
    """SQLite in-memory DB pra testes. Cada teste comeca vazio.

    Redireciona a engine global (app.db.engine) para esta engine via
    monkeypatch, garantindo que o lifespan da app + AuditService vejam
    as mesmas tabelas criadas aqui (sem isso, lifespan roda em conexao
    1 e AuditService em conexao 2 -> "no such table: audit_log").
    """
    from app.db import SessionLocal as GlobalSessionLocal  # noqa: PLC0415
    from app.db import engine as global_engine  # noqa: PLC0415

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    # Redireciona a engine global para a engine deste teste
    monkeypatch.setattr(global_engine, "pool", eng.pool)
    # Redireciona o SessionLocal global para criar sessoes nesta engine
    monkeypatch.setattr(
        GlobalSessionLocal,
        "kw",
        {"bind": eng, "autoflush": False, "autocommit": False, "expire_on_commit": False},
    )
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(eng)


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return {
        "protocolo_id": 123,
        "tipo": "certidao_negativa",
        "valor": 87.50,
        "cliente_cpf_hash": "abc123",
    }
