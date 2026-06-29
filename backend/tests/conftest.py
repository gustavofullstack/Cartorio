"""Test fixtures."""

import os
import warnings as _warnings_module
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# CPython 3.12 / 3.13 bug + pytest interaction: pytest_sessionfinish chama
# warnings.filterwarnings("always", category=DeprecationWarning) e em
# alguns ambientes o isinstance interno do modulo warnings falha com
# "TypeError: isinstance() arg 2 must be a type" (parece ser causado
# por monkey-patching de `int` por algum plugin). Substituimos o
# filterwarnings por uma versao Python pura que NUNCA chama isinstance
# C-level no argumento lineno, usando type(x) is int em vez de isinstance.
_orig_filterwarnings = _warnings_module.filterwarnings


def _safe_filterwarnings(action, message="", category=Warning, module="", lineno=0, append=False):
    # type() is int nao usa C-level isinstance — contorna o bug.
    if type(lineno) is not int:
        lineno = 0
    if type(lineno) is int and lineno < 0:
        lineno = 0
    return _orig_filterwarnings(action, message=message, category=category, module=module, lineno=lineno, append=append)


_warnings_module.filterwarnings = _safe_filterwarnings

# Set test env BEFORE importing app modules.
# Sprint 4 S01: usa setdefault para permitir override via env var
# (CI/prod tem DATABASE_URL=postgresql; dev local pode usar sqlite).
# Se a env var ja esta setada (Postgres), respeita.
# Forca SQLite para testes (default). CI/postgres-tests DEVEM setar
# DATABASE_URL explicitamente ANTES de invocar pytest.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Forca AUDIT_HMAC_KEY mesmo se o shell tiver valor vazio herdado.
# setdefault() nao sobrescreve valor existente (mesmo vazio).
os.environ["AUDIT_HMAC_KEY"] = "a" * 64  # 64 chars hex equivalente pra teste
# Forca TELEGRAM_WEBHOOK_SECRET vazio para que _verify_telegram_secret
# pule validacao HMAC (dev mode) nos testes.
os.environ["TELEGRAM_WEBHOOK_SECRET"] = ""
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
os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY

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
