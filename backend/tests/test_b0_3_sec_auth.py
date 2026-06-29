"""Testes do B0.3.SEC — auth migration dos 7 endpoints com gap P0.3/P0.4/P0.5/P1.3/P1.4/P1.5/P1.6.

Cobre:
- 14 tests de auth gate (2 por endpoint: 200/expected com X-API-Key + 401 sem)
- 1 regression test: list_audit_logs + get_audit_log (commit 5fa154c)
  continuam funcionando pos-migracao.

LGPD art. 37 — todas as tentativas falhas (sem key ou key invalida) sao
audit-logged via require_cartorio_api_key (deps.py:135 hmac.compare_digest
constant-time). Zero inline '!=' em nenhum endpoint.

Endpoints migrados (B0.3.SEC 2026-06-25):
- P0.5 POST /api/v1/audit/verify          (ZERO AUTH -> Depends)
- P1.4 GET  /api/v1/atendimento/ultimas-24h (ZERO AUTH -> Depends)
- P0.3 DELETE /api/v1/cliente/{cliente_id} (inline '!=' -> Depends)
- P0.4 GET  /api/v1/cliente/{cliente_id}/historico (inline '!=' -> Depends)
- P1.3 POST /api/v1/admin/retencao/run    (inline '!=' -> Depends)
- P1.5 POST /api/v1/documento/upload      (inline '!=' -> Depends)
- P1.6 GET  /api/v1/admin/locks           (inline '!=' -> Depends)
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402


AUTH = {"X-API-Key": "a" * 64}


@pytest.fixture
def client():
    import app.models  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.atendimento  # noqa: F401
    import app.models.cliente  # noqa: F401
    import app.models.conversa  # noqa: F401
    import app.models.documento  # noqa: F401
    import app.models.protocolo  # noqa: F401
    import app.models.webhook_event  # noqa: F401

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    import app.db
    import app.main as app_main_module

    original_engine = app.db.engine
    original_session_scope = app.db.session_scope
    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    from contextlib import contextmanager

    @contextmanager
    def test_session_scope():
        s = TestSessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.db.SessionLocal = TestSessionLocal
    app.db.session_scope = test_session_scope

    try:
        with TestClient(app_main_module.app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


# ============================================================================
# P0.5 POST /api/v1/audit/verify
# ============================================================================


def test_audit_verify_com_api_key_valida_retorna_200(client):
    """B0.3.SEC P0.5 — audit verify agora EXIGE X-API-Key (anti side-channel)."""
    resp = client.post("/api/v1/audit/verify", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert "chain_ok" in body
    assert "last_valid_position" in body


def test_audit_verify_sem_api_key_retorna_401(client):
    """B0.3.SEC P0.5 — sem header = 401 UNAUTHORIZED (audit logged em deps.py)."""
    resp = client.post("/api/v1/audit/verify")
    assert resp.status_code == 401


# ============================================================================
# P1.4 GET /api/v1/atendimento/ultimas-24h
# ============================================================================


def test_atendimento_ultimas_24h_com_api_key_valida_retorna_200(client):
    """B0.3.SEC P1.4 — endpoint antes ZERO AUTH agora exige X-API-Key."""
    resp = client.get("/api/v1/atendimento/ultimas-24h", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["window_hours"] == 24
    assert "atendimentos" in body


def test_atendimento_ultimas_24h_sem_api_key_retorna_401(client):
    """B0.3.SEC P1.4 — sem header = 401."""
    resp = client.get("/api/v1/atendimento/ultimas-24h")
    assert resp.status_code == 401


# ============================================================================
# P0.3 DELETE /api/v1/cliente/{cliente_id}
# ============================================================================


def test_delete_cliente_com_api_key_valida_e_cliente_inexistente_retorna_404(client):
    """B0.3.SEC P0.3 — auth gate funciona; 404 vem DEPOIS de passar auth."""
    resp = client.delete("/api/v1/cliente/99999", headers=AUTH)
    assert resp.status_code == 404


def test_delete_cliente_sem_api_key_retorna_401(client):
    """B0.3.SEC P0.3 — sem header = 401 (LGPD art. 18 VI PII protegida)."""
    resp = client.delete("/api/v1/cliente/1")
    assert resp.status_code == 401


# ============================================================================
# P0.4 GET /api/v1/cliente/{cliente_id}/historico
# ============================================================================


def test_cliente_historico_com_api_key_valida_e_cliente_inexistente_retorna_404(client):
    """B0.3.SEC P0.4 — auth gate funciona; 404 vem DEPOIS de passar auth."""
    resp = client.get("/api/v1/cliente/99999/historico", headers=AUTH)
    assert resp.status_code == 404


def test_cliente_historico_sem_api_key_retorna_401(client):
    """B0.3.SEC P0.4 — sem header = 401 (LGPD art. 18 IV PII protegida)."""
    resp = client.get("/api/v1/cliente/1/historico")
    assert resp.status_code == 401


# ============================================================================
# P1.3 POST /api/v1/admin/retencao/run
# ============================================================================


def test_admin_retencao_run_com_api_key_valida_retorna_200(client):
    """B0.3.SEC P1.3 — dry_run default false; retorna resultado."""
    resp = client.post("/api/v1/admin/retencao/run", headers=AUTH, json={"dry_run": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert "scanned" in body


def test_admin_retencao_run_sem_api_key_retorna_401(client):
    """B0.3.SEC P1.3 — sem header = 401 (DPO op D4 retencao)."""
    resp = client.post("/api/v1/admin/retencao/run", json={"dry_run": True})
    assert resp.status_code == 401


# ============================================================================
# P1.5 POST /api/v1/documento/upload
# ============================================================================


def test_documento_upload_com_api_key_valida_retorna_404_para_protocolo_inexistente(client):
    """B0.3.SEC P1.5 — auth gate funciona; 404 vem DEPOIS (protocolo missing)."""
    resp = client.post(
        "/api/v1/documento/upload",
        headers=AUTH,
        data={
            "protocolo_id": "99999",
            "tipo": "rg",
            "storage_path": "s3://bucket/key",
            "mime_type": "application/pdf",
            "hash_sha256": "a" * 64,
        },
    )
    assert resp.status_code == 404  # PROTOCOLO_NOT_FOUND (passou auth)


def test_documento_upload_sem_api_key_retorna_401(client):
    """B0.3.SEC P1.5 — sem header = 401 (PII indireta)."""
    resp = client.post(
        "/api/v1/documento/upload",
        data={
            "protocolo_id": "1",
            "tipo": "rg",
            "storage_path": "s3://bucket/key",
            "mime_type": "application/pdf",
            "hash_sha256": "a" * 64,
        },
    )
    assert resp.status_code == 401


# ============================================================================
# P1.6 GET /api/v1/admin/locks
# ============================================================================


def test_admin_locks_com_api_key_valida_retorna_200(client):
    """B0.3.SEC P1.6 — endpoint admin tool agora exige X-API-Key."""
    resp = client.get("/api/v1/admin/locks", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_known" in body
    assert "active_count" in body
    assert "locks" in body


def test_admin_locks_sem_api_key_retorna_401(client):
    """B0.3.SEC P1.6 — sem header = 401."""
    resp = client.get("/api/v1/admin/locks")
    assert resp.status_code == 401


# ============================================================================
# Regression test — endpoints ja migrados em 5fa154c (LGPD review P0.1+P0.2)
# continuam funcionando apos B0.3.SEC reordenar/expandir Depends
# ============================================================================


def test_regression_5fa154c_audit_list_e_get_continuam_funcionando(client):
    """5fa154c P0.1+P0.2 — list_audit_logs + get_audit_log nao regrediram.

    Gate de nao-regressao: B0.3.SEC adicionou Depends em 7 endpoints.
    Garante que os 2 endpoints ja migrados em 5fa154c continuam auth-gated.
    """
    # list_audit_logs — 200 com key (path e /audit/logs, plural)
    resp = client.get("/api/v1/audit/logs", headers=AUTH)
    assert resp.status_code == 200

    # list_audit_logs — 401 sem key
    resp = client.get("/api/v1/audit/logs")
    assert resp.status_code == 401

    # get_audit_log — 404 com key (id inexistente)
    resp = client.get("/api/v1/audit/logs/99999", headers=AUTH)
    assert resp.status_code == 404

    # get_audit_log — 401 sem key
    resp = client.get("/api/v1/audit/logs/99999")
    assert resp.status_code == 401
