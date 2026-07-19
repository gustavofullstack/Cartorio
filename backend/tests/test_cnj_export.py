"""Regressoes de seguranca do exportador CNJ agregado."""

from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 -- registra todos os modelos e relacionamentos na Base
from app.models.base import Base
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.cnj_export import (
    CNJExportError,
    _canonical_sha256,
    approve_request,
    build_approved_export,
    create_request,
)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _approved_request(db: Session):
    request = create_request(db, reference_period="2026-07", requested_by="dpo-requester")
    return approve_request(
        db,
        request_id=request.id,
        approved_by="dpo-approver",
        reason="Revisao mensal para envio institucional CNJ.",
    )


def test_export_requires_independent_human_approval(db: Session) -> None:
    request = create_request(db, reference_period="2026-07", requested_by="dpo-1")

    with pytest.raises(CNJExportError, match="aprovacao humana"):
        build_approved_export(db, request_id=request.id)
    with pytest.raises(CNJExportError, match="DPO diferente"):
        approve_request(
            db,
            request_id=request.id,
            approved_by="dpo-1",
            reason="Tentativa de autoaprovacao indevida.",
        )


def test_export_is_aggregate_and_never_serializes_source_pii(db: Session) -> None:
    # Valores sentinela nunca podem atravessar a fronteira do artefato CNJ.
    db.add(
        Cliente(
            nome="SENTINEL_NOME_PRIVADO",
            cpf_hash="SENTINEL_CPF_HASH_PRIVADO",
            email="sentinel.private@example.test",
        )
    )
    db.commit()
    cliente_id = db.query(Cliente.id).scalar()
    db.add(
        Protocolo(
            numero="2026-00001",
            cliente_id=cliente_id,
            tipo="escritura",
            canal_origem="telegram",
        )
    )
    db.commit()

    artifact = build_approved_export(db, request_id=_approved_request(db).id)
    serialized = json.dumps(artifact.as_dict(), ensure_ascii=False)

    assert "SENTINEL_NOME_PRIVADO" not in serialized
    assert "SENTINEL_CPF_HASH_PRIVADO" not in serialized
    assert "sentinel.private@example.test" not in serialized
    assert artifact.report["minimization"]["contains_personal_data"] is False
    assert artifact.report["indicators"]["new_data_subjects"] == 1
    assert artifact.report["indicators"]["notarial_protocols_created"] == 1


def test_manifest_hashes_are_verifiable_and_chain_state_is_declared(db: Session) -> None:
    artifact = build_approved_export(db, request_id=_approved_request(db).id)
    manifest_without_hash = {
        key: value for key, value in artifact.manifest.items() if key != "manifest_sha256"
    }

    assert artifact.manifest["report_sha256"] == _canonical_sha256(artifact.report)
    assert artifact.manifest["manifest_sha256"] == _canonical_sha256(manifest_without_hash)
    assert artifact.report["audit_integrity"]["chain_valid"] is True
    assert artifact.report["controls"]["automatic_external_transmission"] is False


def test_export_fails_closed_when_audit_chain_is_invalid(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.cnj_export.AuditService.verify_chain", lambda _db: (False, 0)
    )

    with pytest.raises(CNJExportError, match="cadeia de auditoria invalida"):
        build_approved_export(db, request_id=_approved_request(db).id)


def test_period_validation_rejects_non_calendar_values(db: Session) -> None:
    with pytest.raises(CNJExportError, match="intervalo permitido"):
        create_request(db, reference_period="2026-13", requested_by="dpo-1")
