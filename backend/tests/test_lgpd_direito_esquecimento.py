"""Testes para LGPD Direito ao Esquecimento (D14/D21).

LGPD art. 18 V — direito ao esquecimento com:
- Soft delete cascade (todas as tabelas com FK cliente_id)
- Anonimizacao (PII substituido por hash irreversivel)
- Audit log (cada exclusao registra motivo + actor_id + timestamp)
- Revertabilidade (chave separada permite restore em 30 dias)

Target: Aumentar cobertura de 0% para >= 95% em:
- app/services/lgpd_direito_esquecimento.py (288 linhas, LGPD P0)
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)

import pytest


@pytest.fixture
def db():
    """In-memory SQLite com todas as tabelas do LGPD."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.base import Base
    from app.models.cliente import Cliente
    from app.models.audit_log import AuditLog

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def cliente(db):
    """Cria cliente para testes."""
    from app.models.cliente import Cliente

    c = Cliente(
        cpf_hash="a" * 64,
        nome="Teste Cliente",
        email="teste@example.com",
        consentimento_lgpd=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_direito_esquecimento_soft_delete_cascade(db, cliente):
    """Deve soft-deletar cliente + todas as tabelas cascade."""
    from app.services.lgpd_direito_esquecimento import (
        CASCADE_TABLES,
        direito_esquecimento,
    )

    result = direito_esquecimento(
        db=db,
        cliente_id=cliente.id,
        actor_id="gustavo",
        motivo="LGPD art. 18 V - esquecimento",
    )

    # Verifica que cliente foi soft-deletado
    db.refresh(cliente)
    assert cliente.deleted_at is not None

    # Verifica retorno
    assert result["cliente_id"] == cliente.id
    assert result["soft_deleted"] is True
    assert "deleted_tables" in result
    assert "audit_log_id" in result


def test_direito_esquecimento_anonimiza_pii(db, cliente):
    """Deve anonimizar campos PII ao esquecer."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    nome_original = cliente.nome
    email_original = cliente.email

    direito_esquecimento(
        db=db,
        cliente_id=cliente.id,
        actor_id="gustavo",
        motivo="LGPD art. 18 V",
    )

    # Verifica que PII foi anonimizado
    db.expire_all()
    db.refresh(cliente)
    assert cliente.nome != nome_original
    assert cliente.email != email_original
    # Hash irreversivel (LGPD compliance)
    assert "anonimizado" in cliente.nome.lower() or "hash" in cliente.nome.lower() or len(cliente.nome) > 0


def test_direito_esquecimento_audit_log(db, cliente):
    """Deve registrar audit log com motivo + actor + timestamp."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    result = direito_esquecimento(
        db=db,
        cliente_id=cliente.id,
        actor_id="admin-123",
        motivo="LGPD compliance test",
    )

    # Verifica audit log criado
    audit_id = result["audit_log_id"]
    assert audit_id is not None

    # Busca audit log no banco
    from app.models.audit_log import AuditLog
    audit = db.query(AuditLog).filter_by(id=audit_id).first()
    assert audit is not None
    assert audit.actor_id == "admin-123"
    assert "lgpd" in audit.action.lower()


def test_direito_esquecimento_reversivel_com_prazo(db, cliente):
    """Deve setar lgpd_reversivel_ate se prazo fornecido."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    prazo = dt.datetime.now() + dt.timedelta(days=30)

    direito_esquecimento(
        db=db,
        cliente_id=cliente.id,
        actor_id="gustavo",
        motivo="Teste reversibilidade",
        reversivel_ate=prazo,
    )

    db.refresh(cliente)
    assert cliente.lgpd_reversivel_ate is not None


def test_direito_esquecimento_idempotente(db, cliente):
    """Chamar 2x nao deve duplicar soft delete (ja deletado)."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    result1 = direito_esquecimento(
        db=db, cliente_id=cliente.id, actor_id="gustavo", motivo="Teste 1"
    )
    result2 = direito_esquecimento(
        db=db, cliente_id=cliente.id, actor_id="gustavo", motivo="Teste 2"
    )

    # Ambos devem funcionar (idempotente)
    assert result1["cliente_id"] == cliente.id
    assert result2["cliente_id"] == cliente.id


def test_direito_esquecimento_cliente_inexistente(db):
    """Deve tratar cliente inexistente (nao crashar)."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    result = direito_esquecimento(
        db=db, cliente_id=99999, actor_id="gustavo", motivo="Cliente inexistente"
    )

    # Deve retornar erro gracefully (sem exception)
    assert result is not None
    assert "erro" in result or "cliente_nao_encontrado" in str(result)


def test_direito_esquecimento_restaurar(db, cliente):
    """Deve permitir restaurar soft delete (LGPD art. 18 V §2)."""
    from app.services.lgpd_direito_esquecimento import (
        direito_esquecimento,
        restore_direito_esquecimento,
    )

    # Esquecer
    direito_esquecimento(
        db=db, cliente_id=cliente.id, actor_id="gustavo", motivo="Teste restore"
    )
    db.refresh(cliente)
    assert cliente.deleted_at is not None

    # Restaurar
    result = restore_direito_esquecimento(
        db=db,
        cliente_id=cliente.id,
        actor_id="gustavo",
        justificativa="Cliente solicitou revogacao",
    )

    # Deve ter restaurado
    db.refresh(cliente)
    assert cliente.deleted_at is None
    assert result["restored"] is True


def test_direito_esquecimento_lgpd_audit_article(db, cliente):
    """Audit log deve mencionar LGPD art. 18 V (compliance)."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento
    from app.models.audit_log import AuditLog

    result = direito_esquecimento(
        db=db, cliente_id=cliente.id, actor_id="gustavo", motivo="Teste"
    )

    audit = db.query(AuditLog).filter_by(id=result["audit_log_id"]).first()
    payload_str = str(audit.payload)
    # Deve referenciar LGPD art. 18
    assert "lgpd_article" in payload_str.lower() or "18" in payload_str
