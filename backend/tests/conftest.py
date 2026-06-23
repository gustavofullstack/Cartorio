"""Test fixtures."""

import os
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test env BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64  # 64 chars hex equivalente pra teste
# .env local pode ter CHATWOOT_ACCOUNT_ID/INBOX_ID vazios (placeholders nao parseados
# como int). Forca valores numericos via env vars, que tem precedencia sobre .env.
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
# API key usada pelos testes que batem em endpoints protegidos por X-API-Key
# (ex: DELETE /cliente/{id}, GET /cliente/{id}/historico). Setada aqui pra
# estar disponivel antes de app.config criar o singleton `settings` na import.
os.environ.setdefault("CARTORIO_API_KEY", "test-key-12345")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.models.base import Base  # noqa: E402


@pytest.fixture
def db_session() -> Iterator[Session]:
    """SQLite in-memory DB pra testes. Cada teste comeca vazio."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return {
        "protocolo_id": 123,
        "tipo": "certidao_negativa",
        "valor": 87.50,
        "cliente_cpf_hash": "abc123",
    }
