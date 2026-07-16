"""Testes do webhook de recebimento de logs de deleção do n8n (LGPD Art. 18 / Art. 37 - Wave 2 S2.T2).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

N8N_SECRET = "n8n-deletion-test-secret-2026"


def _compute_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def clean_n8n_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", N8N_SECRET)


def test_n8n_deletion_requires_hmac(clean_n8n_env) -> None:
    """POST /api/v1/integrations/n8n/deletion sem assinatura -> 401."""
    payload = {
        "execution_id": "exec-del-001",
        "target_category": "conversas",
        "deleted_count": 42,
    }
    resp = client.post("/api/v1/integrations/n8n/deletion", json=payload)
    assert resp.status_code == 401
    assert "X-N8N-Signature" in resp.text or "Signature" in resp.headers.get("WWW-Authenticate", "")


def test_n8n_deletion_hmac_invalid(clean_n8n_env) -> None:
    """POST /api/v1/integrations/n8n/deletion com assinatura errada -> 401."""
    payload = {
        "execution_id": "exec-del-002",
        "target_category": "conversas",
        "deleted_count": 10,
    }
    resp = client.post(
        "/api/v1/integrations/n8n/deletion",
        json=payload,
        headers={"X-N8N-Signature": "wrong-signature-hash"},
    )
    assert resp.status_code == 401


def test_n8n_deletion_success(clean_n8n_env, db_session) -> None:
    """POST /api/v1/integrations/n8n/deletion com HMAC valido -> 200 (gravado no audit_log)."""
    payload = {
        "execution_id": "exec-del-003",
        "target_category": "conversas",
        "deleted_count": 15,
        "details": {"reason": "expired_365d"},
    }
    body_bytes = json.dumps(payload, separators=(',', ':')).encode()
    sig = _compute_sig(N8N_SECRET, body_bytes)

    resp = client.post(
        "/api/v1/integrations/n8n/deletion",
        json=payload,
        headers={"X-N8N-Signature": sig},
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "accepted"
    assert res["execution_id"] == "exec-del-003"
    assert res["audit_id"] is not None
    assert res["deleted_count"] == 15

    # Validar se persistiu no audit_log real do banco
    from app.models.audit_log import AuditLog
    entry = db_session.query(AuditLog).filter(AuditLog.id == res["audit_id"]).first()
    assert entry is not None
    assert entry.action == "n8n.deletion"
    assert entry.payload["target_category"] == "conversas"
    assert entry.payload["deleted_count"] == 15


def test_n8n_deletion_idempotency(clean_n8n_env, db_session) -> None:
    """Chamadas duplicadas com o mesmo execution_id retornam idempotent."""
    payload = {
        "execution_id": "exec-del-004",
        "target_category": "clientes",
        "deleted_count": 5,
    }
    body_bytes = json.dumps(payload, separators=(',', ':')).encode()
    sig = _compute_sig(N8N_SECRET, body_bytes)

    # Primeira chamada
    resp1 = client.post(
        "/api/v1/integrations/n8n/deletion",
        json=payload,
        headers={"X-N8N-Signature": sig},
    )
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["status"] == "accepted"
    audit_id = res1["audit_id"]

    # Segunda chamada (duplicada)
    resp2 = client.post(
        "/api/v1/integrations/n8n/deletion",
        json=payload,
        headers={"X-N8N-Signature": sig},
    )
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["status"] == "idempotent"
    assert res2["audit_id"] == audit_id


def test_n8n_deletion_audit_log_fail_soft(clean_n8n_env) -> None:
    """Se a gravacao do audit_log falhar por excecao, endpoint responde 200 (failed) em vez de crashar."""
    payload = {
        "execution_id": "exec-del-005",
        "target_category": "conversas",
        "deleted_count": 2,
    }
    body_bytes = json.dumps(payload, separators=(',', ':')).encode()
    sig = _compute_sig(N8N_SECRET, body_bytes)

    # Simula erro de banco no service
    with patch("app.services.audit.AuditService.log_system_action", side_effect=Exception("DB connection timeout")):
        resp = client.post(
            "/api/v1/integrations/n8n/deletion",
            json=payload,
            headers={"X-N8N-Signature": sig},
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "failed"
        assert res["audit_id"] is None
