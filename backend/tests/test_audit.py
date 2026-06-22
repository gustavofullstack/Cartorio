"""Testes do audit log hash chain - seguranca do cartorio depende disso."""

import pytest

from app.models.audit_log import AuditLog
from app.services.audit import AuditService


def test_log_creates_entry_with_hash(db_session, sample_payload):
    entry = AuditService.log(
        db_session,
        actor_id="user:42",
        action="protocolo.create",
        resource="protocolo:1",
        payload=sample_payload,
    )
    assert entry.id is not None
    assert len(entry.hash) == 64  # SHA256 hex
    assert entry.prev_hash is None  # primeira entrada
    assert len(entry.hmac_signature) == 128  # SHA256 hex de 64 bytes
    db_session.commit()


def test_subsequent_entries_chain_hashes(db_session):
    AuditService.log(db_session, actor_id="u", action="a", resource="r:1", payload={"x": 1})
    AuditService.log(db_session, actor_id="u", action="a", resource="r:2", payload={"x": 2})
    AuditService.log(db_session, actor_id="u", action="a", resource="r:3", payload={"x": 3})
    db_session.commit()

    entries = db_session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    assert len(entries) == 3
    assert entries[0].prev_hash is None
    assert entries[1].prev_hash == entries[0].hash
    assert entries[2].prev_hash == entries[1].hash


def test_verify_chain_passes_for_intact_log(db_session):
    for i in range(5):
        AuditService.log(db_session, actor_id="u", action="t", resource=f"r:{i}", payload={"i": i})
    db_session.commit()
    ok, count = AuditService.verify_chain(db_session)
    assert ok is True
    assert count == 5


def test_tamper_detection_payload_modified(db_session):
    """Se alguem editar o payload retroativamente, verify_chain detecta."""
    AuditService.log(db_session, actor_id="u", action="a", resource="r:1", payload={"valor": 100})
    AuditService.log(db_session, actor_id="u", action="a", resource="r:2", payload={"valor": 200})
    db_session.commit()

    # Atacante altera o payload da primeira entrada
    first = db_session.query(AuditLog).order_by(AuditLog.id.asc()).first()
    first.payload = {"valor": 999}  # tampering
    db_session.commit()

    ok, last_valid = AuditService.verify_chain(db_session)
    assert ok is False
    assert last_valid == 0  # cadeia quebrou na primeira entrada


def test_tamper_detection_entry_deleted(db_session):
    """Delecao de entrada no meio da cadeia eh detectada."""
    for i in range(4):
        AuditService.log(db_session, actor_id="u", action="t", resource=f"r:{i}", payload={"i": i})
    db_session.commit()

    # Deletar entrada do meio
    middle = db_session.query(AuditLog).order_by(AuditLog.id.asc()).all()[1]
    db_session.delete(middle)
    db_session.commit()

    ok, last_valid = AuditService.verify_chain(db_session)
    assert ok is False


def test_hmac_signature_changes_with_payload(db_session, sample_payload):
    e1 = AuditService.log(
        db_session, actor_id="u", action="a", resource="r", payload=sample_payload
    )
    hmac1 = e1.hmac_signature
    db_session.commit()

    # Re-log com mesmo payload mas timestamp diferente = HMAC diferente
    e2 = AuditService.log(
        db_session, actor_id="u", action="a", resource="r", payload=sample_payload
    )
    db_session.commit()

    # Os hashes sao diferentes pq timestamps diferem
    assert e1.hmac_signature != e2.hmac_signature
    assert e1.hash != e2.hash
