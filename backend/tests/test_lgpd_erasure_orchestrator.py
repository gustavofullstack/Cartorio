"""Testes do LGPD Erasure Orchestrator (D23).

Cobre:
- test_erasure_anonimiza_cliente_mantendo_pk
- test_erasure_soft_delete_conversa
- test_erasure_preserva_audit_chain
- test_erasure_idempotente
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.services.lgpd_erasure_orchestrator import (
    ErasureResult,
    count_audit_entries_for_cliente,
    erase_cliente,
    verify_audit_chain_intact,
)


@pytest.fixture
def db() -> Generator[Session, None, None]:
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


@pytest.fixture
def cliente_com_pii(db: Session) -> Cliente:
    """Cliente com PII + 2 conversas (1 ativa, 1 ja soft-deleted)."""
    c = Cliente(
        nome="Joao da Silva",
        cpf_hash="hash_joao_pk_preservado",
        email="joao@example.com",
        telefone_hash="hash_tel_joao",
        consentimento_lgpd=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    # 2 conversas (ambas ativas)
    db.add(
        Conversa(
            cliente_id=c.id,
            canal="whatsapp",
            external_id="5511999999999",
            raw_message_hash="h1",
            raw_message_scrubbed="oi",
            bot_response="ola",
        )
    )
    db.add(
        Conversa(
            cliente_id=c.id,
            canal="telegram",
            external_id="12345",
            raw_message_hash="h2",
            raw_message_scrubbed="protocolo",
            bot_response="consulte_protocolo",
        )
    )
    db.commit()
    return c


@pytest.fixture
def cliente_ja_anonimizado(db: Session) -> Cliente:
    """Cliente que ja passou por erasure (cenario de idempotencia)."""
    c = Cliente(
        nome="[ANONIMIZADO art.18 V]",
        cpf_hash="hash_ja_anon",
        email=None,
        telefone_hash=None,
        consentimento_lgpd=False,
        deleted_at=datetime.now(tz=timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestLGPDErasureOrchestrator:
    """D23 — Orquestrador de erasure LGPD (art. 18 IV/V)."""

    def test_erasure_anonimiza_cliente_mantendo_pk(self, db, cliente_com_pii) -> None:
        """Erasure anonimiza PII mas preserva PK."""
        original_id = cliente_com_pii.id
        original_cpf_hash = cliente_com_pii.cpf_hash

        result = erase_cliente(db, cliente_id=cliente_com_pii.id, actor_id="dpo:test")

        assert isinstance(result, ErasureResult)
        assert result.cliente_id == original_id
        assert result.cliente_anonimizado is True
        assert result.erro is None

        # Recarrega do DB
        db.refresh(cliente_com_pii)
        # PK preservado
        assert cliente_com_pii.id == original_id
        # cpf_hash (ja era hash) preservado
        assert cliente_com_pii.cpf_hash == original_cpf_hash
        # PII anonimizados
        assert cliente_com_pii.nome == "[ANONIMIZADO art.18 V]"
        assert cliente_com_pii.email is None
        assert cliente_com_pii.telefone_hash is None
        assert cliente_com_pii.deleted_at is not None
        assert cliente_com_pii.consentimento_lgpd is False

    def test_erasure_soft_delete_conversa(self, db, cliente_com_pii) -> None:
        """Erasure marca deleted_at em TODAS conversas ativas do titular."""
        result = erase_cliente(db, cliente_id=cliente_com_pii.id)

        # 2 conversas foram soft-deleted
        assert result.conversas_deleted == 2
        # Verifica no DB
        conversas = db.query(Conversa).filter(Conversa.cliente_id == cliente_com_pii.id).all()
        assert len(conversas) == 2  # registros ainda existem (LGPD-by-design)
        for c in conversas:
            assert c.deleted_at is not None

    def test_erasure_preserva_audit_chain(self, db, cliente_com_pii) -> None:
        """Audit log eh PRESERVADO (chain SHA256+HMAC intacta apos erasure)."""
        # Conta entries ANTES
        audit_before = (
            db.query(AuditLog).filter(AuditLog.resource == f"cliente:{cliente_com_pii.id}").count()
        )
        entries_before = db.query(AuditLog).count()

        # Executa erasure
        erase_cliente(db, cliente_id=cliente_com_pii.id)

        # Apos erasure:
        # 1. Audit log dessa cliente tem +1 entry (log do erasure)
        audit_after = (
            db.query(AuditLog).filter(AuditLog.resource == f"cliente:{cliente_com_pii.id}").count()
        )
        assert audit_after == audit_before + 1

        # 2. entries_totais += 1
        entries_after = db.query(AuditLog).count()
        assert entries_after == entries_before + 1

        # 3. Hash chain da audit ESTA INTACTA
        chain_ok, last_valid = verify_audit_chain_intact(db)
        assert chain_ok is True
        assert last_valid == entries_after

        # 4. Entry registrada tem hash + hmac
        new_entry = (
            db.query(AuditLog)
            .filter(AuditLog.resource == f"cliente:{cliente_com_pii.id}")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert new_entry is not None
        assert new_entry.action == "lgpd.erasure.orchestrated"
        assert new_entry.hash is not None and len(new_entry.hash) == 64
        assert new_entry.hmac_signature is not None and len(new_entry.hmac_signature) >= 32

    def test_erasure_idempotente(self, db, cliente_ja_anonimizado) -> None:
        """2 chamadas de erasure no mesmo cliente = idempotente (no-op)."""
        # 1a chamada (cliente ja anonimizado)
        result1 = erase_cliente(db, cliente_id=cliente_ja_anonimizado.id)

        # Deve retornar idempotente=True sem aplicar mudancas adicionais
        assert result1.idempotente is True
        assert result1.cliente_anonimizado is False
        assert result1.conversas_deleted == 0
        assert result1.audit_log_id > 0  # ainda gera audit_log (idempotente != silent)

        # Contar audit entries: 2a chamada NAO gera entrada extra alem do id log
        # (Comentado pq nao usamos — apenas para documentar o invariant)
        # audit_count = (
        #     db.query(AuditLog).filter(AuditLog.resource == f"cliente:{cliente_ja_anonimizado.id}").count()
        # )

        # 2a chamada (deve continuar idempotente)
        result2 = erase_cliente(db, cliente_id=cliente_ja_anonimizado.id)
        assert result2.idempotente is True
        assert result2.cliente_anonimizado is False
        assert result2.conversas_deleted == 0

        # Cliente continua anonimizado (PII intacto no estado anonimizado)
        db.refresh(cliente_ja_anonimizado)
        assert cliente_ja_anonimizado.nome == "[ANONIMIZADO art.18 V]"
        assert cliente_ja_anonimizado.deleted_at is not None

        # Hash chain continua OK
        chain_ok, _last_valid = verify_audit_chain_intact(db)
        assert chain_ok is True

    def test_erasure_cliente_inexistente(self, db) -> None:
        """Cliente nao existe -> resultado com erro, sem audit entry."""
        result = erase_cliente(db, cliente_id=99999)
        assert result.erro == "cliente_nao_encontrado"
        assert result.cliente_anonimizado is False
        assert result.audit_log_id == 0

    def test_erasure_gera_audit_com_action_correto(self, db, cliente_com_pii) -> None:
        """Audit log gerado tem action=lgpd.erasure.orchestrated (LGPD-by-design)."""
        result = erase_cliente(db, cliente_id=cliente_com_pii.id, actor_id="dpo:test")
        audit_entry = db.get(AuditLog, result.audit_log_id)
        assert audit_entry is not None
        assert audit_entry.action == "lgpd.erasure.orchestrated"
        assert audit_entry.actor_type == "dpo"
        assert audit_entry.actor_id == "dpo:test"
        assert audit_entry.resource == f"cliente:{cliente_com_pii.id}"

    def test_erasure_audit_payload_inclui_metadata(self, db, cliente_com_pii) -> None:
        """Audit payload inclui motivo + reversivel_ate + summary."""
        result = erase_cliente(db, cliente_id=cliente_com_pii.id, motivo="cliente_solicitou")
        audit_entry = db.get(AuditLog, result.audit_log_id)
        assert audit_entry is not None
        payload = audit_entry.payload or {}
        assert payload.get("motivo") == "cliente_solicitou"
        assert payload.get("reversivel_ate") is not None
        assert payload.get("lgpd_article") == "art. 18 IV/V"
        assert payload.get("orchestrator_version") == "1.0"

    def test_count_audit_entries_for_cliente(self, db, cliente_com_pii) -> None:
        """count_audit_entries_for_cliente conta entries desse cliente."""
        # Antes do erasure
        assert count_audit_entries_for_cliente(db, cliente_com_pii.id) == 0
        # Apos erasure
        erase_cliente(db, cliente_id=cliente_com_pii.id)
        assert count_audit_entries_for_cliente(db, cliente_com_pii.id) == 1

    def test_erasure_chain_ok_com_multiplas_chamadas(self, db, cliente_com_pii) -> None:
        """Multiplos clientes anonimizados em sequencia — chain permanece intacta."""
        # Cria 3 clientes
        outros = []
        for i in range(3):
            c = Cliente(
                nome=f"Outro {i}",
                cpf_hash=f"hash_outro_{i}",
                email=f"outro{i}@example.com",
                consentimento_lgpd=True,
            )
            db.add(c)
            db.commit()
            db.refresh(c)
            outros.append(c)

        # Erasure sequencial
        erase_cliente(db, cliente_id=cliente_com_pii.id, actor_id="dpo:cascata_1")
        for c in outros:
            erase_cliente(db, cliente_id=c.id, actor_id="dpo:cascata_n")

        # 4 entries geradas (1 + 3) — chain mantida
        chain_ok, last_valid = verify_audit_chain_intact(db)
        assert chain_ok is True
        # Total de audit entries >= 4 + sistema entries (startup, etc)
        assert last_valid >= 4
