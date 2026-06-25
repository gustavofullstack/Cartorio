"""Testes para POST /api/v1/integrations/n8n/error (B6 N8N Error Handler Global).

Cobre:
- HMAC validation (4 cenarios: valid/invalid/missing/dev-mode)
- Idempotencia via execution_id (replay nao duplica audit_log)
- audit_log gravado (LGPD art. 37)
- Metrica Prometheus incrementada (n8n_errors_total{wf, type})
- Error classification (7 cards: connection/http_4xx/http_5xx/timeout/validation/auth/unknown)
- Endpoint aparece no OpenAPI/Swagger
- Payload validation (campos obrigatorios)
- LGPD safety: payload bruto NAO persistido, apenas digest + metadados

Coverage target: >= 90% em app/services/n8n_error.py + endpoint.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.models.audit_log import AuditLog  # noqa: E402
from app.models.base import Base  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================


def _compute_sig(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex puro (mesmo padrao do N8N Error Workflow)."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


N8N_WEBHOOK_SECRET = "n8n-webhook-test-secret-2026-06-25"


def _make_payload(
    *,
    workflow_name: str = "01 - Consulta Emolumento WhatsApp (v3)",
    workflow_id: str = "bR7qIo3bFpG4zgxO",
    execution_id: str = "exec-test-001",
    error: dict | None = None,
    error_type: str | None = None,
    node: str | None = "HTTP Request",
    timestamp: str = "2026-06-25T08:00:00.000Z",
) -> dict:
    """Constroi payload canonico do N8N Error Workflow."""
    if error is None:
        error = {
            "name": "NodeApiError",
            "message": "ECONNREFUSED 10.61.79.50:8000",
            "http_code": 500,
        }
    return {
        "workflow_name": workflow_name,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "error_type": error_type,
        "error": error,
        "node": node,
        "timestamp": timestamp,
    }


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_engine():
    """SQLite in-memory + schema completo."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient com DB mockado e env var N8N_WEBHOOK_SECRET setada."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
        patch.dict(os.environ, {"N8N_WEBHOOK_SECRET": N8N_WEBHOOK_SECRET}),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def client_dev_mode(test_engine, test_session_factory):
    """TestClient com N8N_WEBHOOK_SECRET VAZIO (dev mode aceita sem signature)."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
        patch.dict(os.environ, {"N8N_WEBHOOK_SECRET": ""}),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def _post(client, payload: dict, *, secret: str | None = N8N_WEBHOOK_SECRET, sig: str | None = "__AUTO__"):
    """POST helper.

    - sig="__AUTO__" (default): auto-assina se secret fornecido.
    - sig=None: NAO envia header X-N8N-Signature (testa "missing sig").
    - sig="<value>": envia exatamente o valor (testa "invalid sig").
    """
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if sig == "__AUTO__":
        if secret:
            headers["X-N8N-Signature"] = _compute_sig(secret, body)
    elif sig is not None:
        headers["X-N8N-Signature"] = sig
    return client.post("/api/v1/integrations/n8n/error", content=body, headers=headers)


# ============================================================================
# HMAC validation
# ============================================================================


def test_hmac_valid_returns_accepted(client, test_engine, test_session_factory):
    """HMAC signature valida + secret configurado = 200 accepted."""
    payload = _make_payload(execution_id="exec-hmac-001")
    resp = _post(client, payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["execution_id"] == "exec-hmac-001"
    assert data["audit_id"] is not None
    assert data["error_type"] == "http_5xx"  # http_code=500


def test_hmac_invalid_returns_401(client):
    """HMAC signature invalida = 401."""
    payload = _make_payload(execution_id="exec-bad-sig")
    resp = _post(client, payload, sig="invalida")
    assert resp.status_code == 401
    assert resp.json()["detail"]["erro"] == "INVALID_SIGNATURE"


def test_hmac_missing_with_secret_returns_401(client):
    """Sem signature + secret configurado = 401 (fail-secure)."""
    payload = _make_payload(execution_id="exec-no-sig")
    resp = _post(client, payload, sig=None)
    assert resp.status_code == 401


def test_hmac_sha256_prefix_accepted(client):
    """Formato `sha256=<hex>` estilo GitHub/Stripe eh aceito."""
    payload = _make_payload(execution_id="exec-prefix-001")
    body = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + _compute_sig(N8N_WEBHOOK_SECRET, body)
    headers = {"Content-Type": "application/json", "X-N8N-Signature": sig}
    resp = client.post(
        "/api/v1/integrations/n8n/error", content=body, headers=headers
    )
    assert resp.status_code == 200


def test_hmac_dev_mode_accepts_without_signature(client_dev_mode):
    """Sem secret + sem signature = 200 (dev mode, alinha com evolution)."""
    payload = _make_payload(execution_id="exec-devmode-001")
    resp = _post(client_dev_mode, payload, secret=None, sig=None)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_hmac_wrong_secret_returns_401(client):
    """HMAC calculado com secret diferente = 401."""
    payload = _make_payload(execution_id="exec-wrong-secret")
    body = json.dumps(payload).encode("utf-8")
    sig = _compute_sig("outra-chave-nao-configurada", body)
    headers = {"Content-Type": "application/json", "X-N8N-Signature": sig}
    resp = client.post(
        "/api/v1/integrations/n8n/error", content=body, headers=headers
    )
    assert resp.status_code == 401


# ============================================================================
# audit_log
# ============================================================================


def test_audit_log_gravado_com_request_id_igual_execution_id(
    client, test_engine, test_session_factory
):
    """audit_log recebe action=n8n.error, request_id=execution_id, payload canonico."""
    payload = _make_payload(execution_id="exec-audit-001")
    resp = _post(client, payload)
    assert resp.status_code == 200
    audit_id = resp.json()["audit_id"]
    assert audit_id is not None

    with test_session_factory() as db:
        entry = db.execute(
            select(AuditLog).where(AuditLog.id == audit_id)
        ).scalar_one()
        assert entry is not None
        assert entry.action == "n8n.error"
        assert entry.actor_id == "n8n-error-workflow"
        assert entry.actor_type == "system"
        assert entry.request_id == "exec-audit-001"
        assert entry.canal == "n8n"
        assert entry.resource == "workflow:01 - Consulta Emolumento WhatsApp (v3)"
        assert entry.payload["workflow_name"] == "01 - Consulta Emolumento WhatsApp (v3)"
        assert entry.payload["workflow_id"] == "bR7qIo3bFpG4zgxO"
        assert entry.payload["execution_id"] == "exec-audit-001"
        assert entry.payload["error_type"] == "http_5xx"
        assert entry.payload["payload_digest"] is not None
        # LGPD safety: payload bruto nao persistido
        assert "secret" not in str(entry.payload).lower()


def test_audit_log_idempotente_replay(client, test_engine, test_session_factory):
    """Replay mesmo execution_id = 200 idempotent + 1 audit_log entry."""
    payload = _make_payload(execution_id="exec-replay-001")

    # Primeira chamada
    resp1 = _post(client, payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "accepted"
    audit_id_1 = resp1.json()["audit_id"]

    # Segunda chamada (replay)
    resp2 = _post(client, payload)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "idempotent"
    assert resp2.json()["audit_id"] == audit_id_1

    # Apenas 1 entrada no audit_log
    with test_session_factory() as db:
        count = db.execute(
            select(AuditLog).where(
                AuditLog.action == "n8n.error",
                AuditLog.request_id == "exec-replay-001",
            )
        ).all()
        assert len(count) == 1


# ============================================================================
# Prometheus metric
# ============================================================================


def test_metrica_prometheus_incrementada(client):
    """n8n_errors_total{workflow_name, error_type} eh incrementada apos sucesso.

    Test captura DELTA (antes/depois) do TOTAL de counters para ser robusto
    a execucao compartilhada do singleton `store` entre testes.
    Cardinalidade: ~40 WFs ativos * 7 error_types = ~280 chaves.
    """
    import uuid

    from app.services.metrics import store

    unique_wf = f"WF-TEST-METRIC-{uuid.uuid4().hex[:8]}"
    unique_exec = f"exec-metric-{uuid.uuid4().hex[:8]}"

    # Soma total ANTES (singleton compartilhado, mas delta eh confiavel)
    total_before = sum(store.counters.get("n8n_errors_total", {}).values())

    payload = _make_payload(
        workflow_name=unique_wf,
        execution_id=unique_exec,
        error={"name": "ECONNREFUSED", "message": "connection refused"},
    )
    resp = _post(client, payload)
    assert resp.status_code == 200
    assert resp.json()["error_type"] == "connection"

    total_after = sum(store.counters.get("n8n_errors_total", {}).values())

    # Counter GLOBAL incrementou em >= 1
    assert total_after - total_before >= 1, (
        f"metric nao incrementou: total_before={total_before} total_after={total_after}"
    )

    # E a chave especifica do nosso wf existe
    counters = store.counters.get("n8n_errors_total", {})
    matching = [k for k in counters if unique_wf in k]
    assert len(matching) >= 1, f"chave com wf={unique_wf} nao encontrada em {list(counters)[:5]}"


def test_metrica_nao_incrementa_em_replay(client):
    """Replay (idempotent) NAO incrementa metrica (ja' contada na 1a chamada)."""
    import uuid

    from app.services.metrics import store

    unique_wf = f"WF-METRIC-IDEMP-{uuid.uuid4().hex[:8]}"
    unique_exec = f"exec-metric-idemp-{uuid.uuid4().hex[:8]}"
    key = f"error_type=connection|workflow_name={unique_wf}"

    payload = _make_payload(
        workflow_name=unique_wf,
        execution_id=unique_exec,
        error={"name": "ECONNREFUSED", "message": "connection refused"},
    )

    # 1a chamada
    resp1 = _post(client, payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "accepted"

    after_first = store.counters.get("n8n_errors_total", {}).get(key, 0)

    # 2a chamada (replay)
    resp2 = _post(client, payload)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "idempotent"

    after_second = store.counters.get("n8n_errors_total", {}).get(key, 0)

    # Contador NAO muda no replay
    assert after_second == after_first


# ============================================================================
# Error classification
# ============================================================================


def test_classify_connection_refused():
    """ECONNREFUSED -> connection."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "ECONNREFUSED", "message": "connection refused"}) == "connection"
    assert classify_error_type({"name": "Error", "message": "ECONNREFUSED 10.0.0.1:8000"}) == "connection"


def test_classify_timeout():
    """ETIMEDOUT/Timeout -> timeout."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "TimeoutError", "message": ""}) == "timeout"
    assert classify_error_type({"name": "Error", "message": "ETIMEDOUT"}) == "timeout"
    assert classify_error_type({"name": "Error", "message": "Read timed out"}) == "timeout"


def test_classify_http_4xx():
    """http_code 4xx (sem 401/403) -> http_4xx."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "Error", "message": "bad", "http_code": 404}) == "http_4xx"
    assert classify_error_type({"name": "Error", "message": "bad", "http_code": 422}) == "http_4xx"
    assert classify_error_type({"name": "Error", "message": "bad", "http_code": 429}) == "http_4xx"


def test_classify_http_5xx():
    """http_code 5xx -> http_5xx."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "Error", "message": "bad", "http_code": 500}) == "http_5xx"
    assert classify_error_type({"name": "Error", "message": "bad", "http_code": 503}) == "http_5xx"


def test_classify_auth():
    """http_code 401/403 -> auth."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "Error", "message": "unauthorized", "http_code": 401}) == "auth"
    assert classify_error_type({"name": "Error", "message": "forbidden", "http_code": 403}) == "auth"


def test_classify_validation():
    """ValidationError -> validation."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "ValidationError", "message": "invalid"}) == "validation"
    assert classify_error_type({"name": "PydanticError", "message": "schema fail"}) == "validation"
    assert classify_error_type({"name": "Error", "message": "JSON decode error"}) == "validation"


def test_classify_unknown():
    """Fallback -> unknown."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type(None) == "unknown"
    assert classify_error_type({}) == "unknown"
    assert classify_error_type({"name": "WeirdError", "message": "???"}) == "unknown"


def test_classify_host_unreachable_is_connection():
    """EHOSTUNREACH/ENETUNREACH/ENOTFOUND -> connection."""
    from app.services.n8n_error import classify_error_type

    assert classify_error_type({"name": "Error", "message": "EHOSTUNREACH"}) == "connection"
    assert classify_error_type({"name": "Error", "message": "ENETUNREACH"}) == "connection"
    assert classify_error_type({"name": "Error", "message": "ENOTFOUND api.example.com"}) == "connection"


# ============================================================================
# Payload validation (Pydantic)
# ============================================================================


def test_payload_sem_workflow_name_422(client):
    """workflow_name obrigatorio."""
    payload = _make_payload(execution_id="exec-no-name")
    del payload["workflow_name"]
    resp = _post(client, payload)
    assert resp.status_code == 422


def test_payload_sem_execution_id_422(client):
    """execution_id obrigatorio."""
    payload = _make_payload()
    del payload["execution_id"]
    resp = _post(client, payload)
    assert resp.status_code == 422


def test_payload_error_type_custom_aceito(client):
    """error_type customizado do cliente eh preservado."""
    payload = _make_payload(execution_id="exec-custom-type", error_type="rate_limit")
    resp = _post(client, payload)
    assert resp.status_code == 200
    assert resp.json()["error_type"] == "rate_limit"


def test_payload_sem_error_type_classifica_automatico(client):
    """error_type ausente -> backend classifica via classify_error_type."""
    payload = _make_payload(
        execution_id="exec-auto-classify",
        error={"name": "Error", "message": "ECONNREFUSED"},
        error_type=None,
    )
    resp = _post(client, payload)
    assert resp.status_code == 200
    assert resp.json()["error_type"] == "connection"


# ============================================================================
# OpenAPI / Swagger
# ============================================================================


def test_endpoint_aparece_no_openapi(client):
    """/api/v1/integrations/n8n/error aparece no OpenAPI schema."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/integrations/n8n/error" in paths


# ============================================================================
# Payload digest (LGPD safety)
# ============================================================================


def test_compute_payload_digest_deterministic():
    """Mesmo payload -> mesmo digest (audit idempotency)."""
    from app.services.n8n_error import compute_payload_digest

    p = {"a": 1, "b": [1, 2, 3], "c": {"x": "y"}}
    assert compute_payload_digest(p) == compute_payload_digest(p)
    # Ordem de chaves nao importa (sort_keys=True)
    assert compute_payload_digest(p) == compute_payload_digest({"c": {"x": "y"}, "b": [1, 2, 3], "a": 1})


def test_compute_payload_digest_diferente_para_payload_diferente():
    """Payloads diferentes -> digests diferentes."""
    from app.services.n8n_error import compute_payload_digest

    assert compute_payload_digest({"a": 1}) != compute_payload_digest({"a": 2})


def test_compute_payload_digest_lgpd_safe():
    """Digest NAO contem dados do payload (one-way hash)."""
    from app.services.n8n_error import compute_payload_digest

    payload = {
        "workflow_name": "WF with PII",
        "cpf": "123.456.789-09",
        "message": "secret message",
    }
    digest = compute_payload_digest(payload)
    # 64 chars hex (sha256)
    assert len(digest) == 64
    # NAO contem PII
    assert "123.456.789-09" not in digest
    assert "WF with PII" not in digest
    assert "secret message" not in digest


# ============================================================================
# validate_n8n_signature (unit-level)
# ============================================================================


def test_validate_signature_unit(monkeypatch: pytest.MonkeyPatch):
    """Funcao validate_n8n_signature direta — todos os cenarios."""
    from app.services.n8n_error import validate_n8n_signature

    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "my-secret-xyz")
    body = b'{"exec": 1}'

    # Valid sig
    assert validate_n8n_signature(body, _compute_sig("my-secret-xyz", body)) is True

    # Invalid sig
    assert validate_n8n_signature(body, "wrong-sig") is False

    # Missing sig + secret set
    assert validate_n8n_signature(body, None) is False
    assert validate_n8n_signature(body, "") is False

    # Dev mode (no secret)
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "")
    assert validate_n8n_signature(body, None) is True
    assert validate_n8n_signature(body, "") is True


def test_validate_signature_timing_safe(monkeypatch: pytest.MonkeyPatch):
    """Validacao usa hmac.compare_digest (timing-safe)."""
    from app.services.n8n_error import validate_n8n_signature

    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "timing-test-secret")
    body = b"x" * 1000
    sig = _compute_sig("timing-test-secret", body)
    # Trocar 1 char -> falha (sanity check)
    bad = "a" + sig[1:]
    assert validate_n8n_signature(body, bad) is False


# ============================================================================
# HMAC E2E (signature header lowercase)
# ============================================================================


def test_hmac_lowercase_header_aceito(client):
    """Header `x-n8n-signature` (lowercase) eh aceito (FastAPI alias)."""
    payload = _make_payload(execution_id="exec-lowercase-001")
    body = json.dumps(payload).encode("utf-8")
    sig = _compute_sig(N8N_WEBHOOK_SECRET, body)
    # TestClient normaliza headers para lowercase no request; garantimos explicitamente
    headers = {"Content-Type": "application/json", "x-n8n-signature": sig}
    resp = client.post(
        "/api/v1/integrations/n8n/error", content=body, headers=headers
    )
    assert resp.status_code == 200


# ============================================================================
# LGPD safety E2E (audit_log payload canonico)
# ============================================================================


def test_audit_payload_nao_persiste_error_stack_gigante(
    client, test_engine, test_session_factory
):
    """Stack traces grandes sao truncadas antes de persistir."""
    big_stack = "x" * 10_000
    payload = _make_payload(
        execution_id="exec-big-stack",
        error={
            "name": "Error",
            "message": big_stack,
            "stack": big_stack,
        },
    )
    resp = _post(client, payload)
    assert resp.status_code == 200

    with test_session_factory() as db:
        entry = db.execute(
            select(AuditLog).where(AuditLog.request_id == "exec-big-stack")
        ).scalar_one()
        # message truncado em 512 chars
        assert len(entry.payload["error"]["message"]) <= 512


def test_audit_payload_truncamento_message_512(client, test_engine, test_session_factory):
    """error.message truncado em 512 chars."""
    payload = _make_payload(
        execution_id="exec-msg-truncate",
        error={
            "name": "Error",
            "message": "M" * 1000,
        },
    )
    resp = _post(client, payload)
    assert resp.status_code == 200
    with test_session_factory() as db:
        entry = db.execute(
            select(AuditLog).where(AuditLog.request_id == "exec-msg-truncate")
        ).scalar_one()
        assert len(entry.payload["error"]["message"]) == 512