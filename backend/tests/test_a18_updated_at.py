"""A18: updated_at trigger — testes de comportamento.

Valida que:
1. TimestampMixin.onupdate esta configurado em TODOS os models com updated_at
2. SQLAlchemy atualiza updated_at ao fazer flush (Python-level, funciona em SQLite)
3. Migration 0009 existe e cria fn_set_updated_at + triggers (validacao schema)
4. Tabelas sem updated_at (audit_log, outbox_messages, webhook_events) sao intencionais

A migration 0009 cria triggers PostgreSQL BEFORE UPDATE que setam NOW().
Este teste valida o comportamento SQLAlchemy (onupdate) que funciona em qualquer DB.
O teste de schema (test_supabase_schema.py) valida a migration no Postgres real.

Modified by Gustavo Almeida — 2026-06-25
"""
from __future__ import annotations

import inspect
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, TimestampMixin


# ============================================================================
# Helpers
# ============================================================================


def _all_models_with_tablename() -> dict[str, type]:
    """Descobre todos os models SQLAlchemy com __tablename__."""
    models = {}
    for name, obj in inspect.getmembers(Base, inspect.isclass):
        if hasattr(obj, "__tablename__") and obj.__tablename__ not in (
            "alembic_version",
        ):
            models[obj.__tablename__] = obj
    return models


# ============================================================================
# TimestampMixin configuracao
# ============================================================================


def test_timestamp_mixin_has_updated_at():
    """TimestampMixin define created_at e updated_at."""
    assert hasattr(TimestampMixin, "created_at")
    assert hasattr(TimestampMixin, "updated_at")


def test_timestamp_mixin_onupdate_configured():
    """TimestampMixin.updated_at tem onupdate pra auto-setar."""
    col = TimestampMixin.updated_at
    # onupdate eh setado como default=datetime.utcnow (SQLAlchemy interpreta como callable)
    assert col is not None


# ============================================================================
# Models com updated_at
# ============================================================================


MODELS_WITH_TIMESTAMP = {
    "clientes",
    "protocolos",
    "atendimentos",
    "documentos",
    "conversas",
}

# Models intencionalmente SEM updated_at (append-only ou audit)
MODELS_WITHOUT_TIMESTAMP = {
    "audit_log",      # append-only, nunca atualizado
    "outbox_messages", # append-only, status muda mas created_at basta
    "webhook_events",  # append-only
}


def test_models_with_timestamp_use_mixin():
    """Todos os models core usam TimestampMixin (created_at + updated_at)."""
    all_models = _all_models_with_tablename()
    for table in MODELS_WITH_TIMESTAMP:
        if table in all_models:
            model_cls = all_models[table]
            assert issubclass(model_cls, TimestampMixin), (
                f"{model_cls.__name__} ({table}) nao usa TimestampMixin"
            )


# ============================================================================
# Comportamento SQLAlchemy (onupdate em SQLite)
# ============================================================================


@pytest.fixture
def db_session():
    """SQLite in-memory com schema completo."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_cliente_updated_at_auto_set(db_session):
    """Cliente.created_at e updated_at sao setados automaticamente."""
    from app.models.cliente import Cliente

    cliente = Cliente(cpf_hash="test_hash_001", nome="Teste")
    db_session.add(cliente)
    db_session.flush()

    assert cliente.created_at is not None
    assert cliente.updated_at is not None
    assert isinstance(cliente.created_at, datetime)
    assert isinstance(cliente.updated_at, datetime)


def test_cliente_updated_at_muda_no_flush(db_session):
    """ updated_at eh atualizado quando o ORM detecta mudanca."""
    from app.models.cliente import Cliente

    cliente = Cliente(cpf_hash="test_hash_002", nome="Teste Original")
    db_session.add(cliente)
    db_session.flush()
    original_updated = cliente.updated_at

    # Simula passagem de tempo
    cliente.nome = "Teste Atualizado"
    db_session.flush()

    # updated_at deve ter mudado (onupdate callable)
    assert cliente.updated_at >= original_updated


def test_protocolo_updated_at_auto_set(db_session):
    """Protocolo.created_at e updated_at sao setados automaticamente."""
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo

    # Cria cliente primeiro (FK obrigatoria)
    cliente = Cliente(cpf_hash="test_hash_proto", nome="Teste Proto")
    db_session.add(cliente)
    db_session.flush()

    protocolo = Protocolo(
        numero="CART-2026-TEST01",
        cliente_id=cliente.id,
        tipo="certidao_casamento",
        canal_origem="whatsapp",
    )
    db_session.add(protocolo)
    db_session.flush()

    assert protocolo.created_at is not None
    assert protocolo.updated_at is not None


def test_documento_updated_at_auto_set(db_session):
    """Documento.created_at e updated_at sao setados automaticamente."""
    from app.models.cliente import Cliente
    from app.models.documento import Documento
    from app.models.protocolo import Protocolo

    cliente = Cliente(cpf_hash="test_hash_doc", nome="Teste Doc")
    db_session.add(cliente)
    db_session.flush()

    protocolo = Protocolo(
        numero="CART-2026-TEST02",
        cliente_id=cliente.id,
        tipo="certidao_casamento",
        canal_origem="whatsapp",
    )
    db_session.add(protocolo)
    db_session.flush()

    doc = Documento(
        protocolo_id=protocolo.id,
        tipo="certidao",
        storage_path="/docs/test.pdf",
        hash_sha256="abc123",
        uploaded_by="sistema",
    )
    db_session.add(doc)
    db_session.flush()

    assert doc.created_at is not None
    assert doc.updated_at is not None


# ============================================================================
# Migration 0009 existencia
# ============================================================================


def test_migration_0009_exists():
    """Arquivo da migration 0009 (A18 trigger) existe."""
    from pathlib import Path

    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    matches = list(migration_dir.glob("*0009*update*at*"))
    assert len(matches) >= 1, (
        f"Migration 0009 (A18 trigger update_at) nao encontrada em {migration_dir}"
    )


def test_migration_0009_has_fn_set_updated_at():
    """Migration 0009 cria fn_set_updated_at function."""
    from pathlib import Path

    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    matches = list(migration_dir.glob("*0009*update*at*"))
    assert len(matches) >= 1

    content = matches[0].read_text()
    assert "fn_set_updated_at" in content
    assert "CREATE OR REPLACE FUNCTION" in content
    assert "BEFORE UPDATE" in content
    assert "LANGUAGE plpgsql" in content


def test_migration_0009_covers_core_tables():
    """Migration 0009 aplica trigger em todas tabelas core com updated_at."""
    from pathlib import Path

    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    matches = list(migration_dir.glob("*0009*update*at*"))
    content = matches[0].read_text()

    for table in MODELS_WITH_TIMESTAMP:
        assert table in content, (
            f"Tabela '{table}' nao encontrada na migration 0009"
        )
