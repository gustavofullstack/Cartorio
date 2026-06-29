"""Testes do endpoint POST /api/v1/metrics/n8n (B0.1 - Sprint 3).

Cobre:
- Auth: 401 sem X-API-Key, 401 com chave invalida, 200 com chave valida
- Payload canonico: counters/gauges/uptime_seconds/workflows_active/memory_rss_mb
  -> MetricsStore atualizado com label source=n8n
- Payload prometheus_raw: parse linha-a-linha (subset minimo)
- Payload unknown: aceito, logado como unknown, retorna 200 (workflow nao quebra)
- Audit log: action=metrics.n8n_received registrado com LGPD-safe payload
- LGPD: counters/gauges tem label source=n8n (separa de metrics internas)

Referencia: Sprint 3 B0.1 (PLAN_GIGANTE_2026-06-24.md) - corrige 404
recorrente do workflow #25 N8N Metrics Collector (1 erro/min desde 2026-06-23).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

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


TEST_API_KEY = "a" * 64


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.models.base import Base
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

    the_app = app_main_module.app
    try:
        with TestClient(the_app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


# ============================================================================
# Auth tests
# ============================================================================


def test_post_metrics_n8n_sem_api_key_retorna_401(client: TestClient) -> None:
    """Sem X-API-Key deve retornar 401."""
    resp = client.post(
        "/api/v1/metrics/n8n",
        json={"uptime_seconds": 100.0},
    )
    assert resp.status_code == 401
    body = resp.json()
    detail = body.get("detail", {})
    # API retorna 'UNAUTHORIZED' (ou legado API_KEY_AUSENTE/INVALIDA)
    assert detail.get("erro") in ("UNAUTHORIZED", "API_KEY_AUSENTE", "API_KEY_INVALIDA")


def test_post_metrics_n8n_com_api_key_invalida_retorna_401(client: TestClient) -> None:
    """Com X-API-Key errada deve retornar 401."""
    resp = client.post(
        "/api/v1/metrics/n8n",
        json={"uptime_seconds": 100.0},
        headers={"X-API-Key": "chave-errada-nao-bate"},
    )
    assert resp.status_code == 401
    body = resp.json()
    detail = body.get("detail", {})
    assert detail.get("erro") in ("UNAUTHORIZED", "API_KEY_INVALIDA")


# ============================================================================
# Payload canonico
# ============================================================================


def test_post_metrics_n8n_canonical_com_counters_e_gauges(client: TestClient) -> None:
    """Payload canonico com counters/gauges deve ser ingerido no MetricsStore."""
    payload = {
        "counters": {
            "n8n_executions_total": {"workflow=25|status=ok": 42},
        },
        "gauges": {
            "n8n_memory_rss_mb_dict": {"instance=main": 256.5},
        },
        "uptime_seconds": 1234.5,
        "workflows_active": 33,
        "memory_rss_mb": 256.5,
        "timestamp": "2026-06-24T15:00:00Z",
    }

    resp = client.post(
        "/api/v1/metrics/n8n",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["received"] is True
    assert body["payload_kind"] == "canonical"
    assert body["counters_ingested"] == 1
    # gauges_ingested inclui: 1 (memory_rss_mb_dict) + 1 (uptime) + 1 (workflows_active) + 1 (memory_rss_mb)
    assert body["gauges_ingested"] >= 3
    assert body["metrics_size_bytes"] > 0
    assert body["audit_action"] == "metrics.n8n_received"


def test_post_metrics_n8n_canonical_minimo_apenas_uptime(client: TestClient) -> None:
    """Payload canonico minimo (soh uptime) deve funcionar."""
    resp = client.post(
        "/api/v1/metrics/n8n",
        json={"uptime_seconds": 60.0},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["payload_kind"] == "canonical"
    assert body["counters_ingested"] == 0
    assert body["gauges_ingested"] == 1


# ============================================================================
# Payload prometheus_raw
# ============================================================================


def test_post_metrics_n8n_prometheus_raw_eh_parseado(client: TestClient) -> None:
    """Payload prometheus_raw (string Prometheus) deve ser parseado."""
    prometheus_text = (
        "# HELP n8n_uptime_seconds Uptime N8N\n"
        "# TYPE n8n_uptime_seconds gauge\n"
        'n8n_uptime_seconds{instance="main"} 3600.5\n'
        "# TYPE n8n_requests_total counter\n"
        'n8n_requests_total{endpoint="/webhook/consulta-emolumento",status="200"} 142\n'
    )

    resp = client.post(
        "/api/v1/metrics/n8n",
        json={"raw": prometheus_text},
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["payload_kind"] == "prometheus_raw"
    assert body["counters_ingested"] >= 1
    assert body["gauges_ingested"] >= 1


# ============================================================================
# Payload unknown (LGPD-by-design: nunca quebra o workflow)
# ============================================================================


def test_post_metrics_n8n_unknown_shape_aceito_sem_quebrar(client: TestClient) -> None:
    """Payload com shape desconhecido deve ser aceito (200) sem quebrar workflow."""
    payload_estranho = {"foo": "bar", "random_number": 42, "nested": {"a": [1, 2, 3]}}

    resp = client.post(
        "/api/v1/metrics/n8n",
        json=payload_estranho,
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["received"] is True
    assert body["payload_kind"] == "unknown"
    assert body["counters_ingested"] == 0
    assert body["gauges_ingested"] == 0


def test_post_metrics_n8n_vazio_aceito_como_unknown(client: TestClient) -> None:
    """Payload vazio deve ser aceito como unknown (LGPD-by-design, nao quebra workflow)."""
    resp = client.post(
        "/api/v1/metrics/n8n",
        json={},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["payload_kind"] == "unknown"


# ============================================================================
# Audit log + label source=n8n (LGPD defense)
# ============================================================================


def test_post_metrics_n8n_label_source_n8n_no_metrics_store(client: TestClient) -> None:
    """Metrics ingeridas devem ter label source=n8n (LGPD + isolamento)."""
    from app.services.metrics import store as metrics_store

    resp = client.post(
        "/api/v1/metrics/n8n",
        json={
            "counters": {"n8n_test_counter": {"k=v": 1}},
            "uptime_seconds": 10.0,
        },
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200

    # Procura o counter n8n_test_counter com label source=n8n
    found_n8n_label = False
    for name, buckets in metrics_store.counters.items():
        if name != "n8n_test_counter":
            continue
        for labels_key in buckets:
            if "source=n8n" in labels_key:
                found_n8n_label = True
                break
    assert found_n8n_label, (
        f"Counter n8n_test_counter sem label source=n8n. "
        f"Counters disponiveis: {list(metrics_store.counters.keys())}"
    )


# ============================================================================
# Helpers (unit tests sem precisar de client)
# ============================================================================


@pytest.mark.parametrize(
    "label_key,expected",
    [
        ("k=v", {"k": "v"}),
        ("k1=v1|k2=v2", {"k1": "v1", "k2": "v2"}),
        ("", {}),
        ("sem_igual", {}),
    ],
)
def test_parse_labels_key_safe(label_key: str, expected: dict) -> None:
    """_parse_labels_key_safe deve parsear de forma segura (sem explodir)."""
    from app.api.v1.router import _parse_labels_key_safe

    assert _parse_labels_key_safe(label_key) == expected


def test_parse_labels_key_safe_trunca_valores_longos() -> None:
    """_parse_labels_key_safe deve truncar valores > 64 chars (LGPD defense)."""
    from app.api.v1.router import _parse_labels_key_safe

    big_value = "x" * 100
    result = _parse_labels_key_safe(f"k={big_value}")
    # Valor longo eh descartado silenciosamente (defesa contra PII acidental)
    assert "k" not in result or len(result.get("k", "")) <= 64


def test_looks_like_prometheus_detecta() -> None:
    """_looks_like_prometheus deve identificar formato Prometheus."""
    from app.api.v1.router import _looks_like_prometheus

    assert _looks_like_prometheus("metric_name 42.0") is True
    assert _looks_like_prometheus('metric_name{label="val"} 42.0') is True
    assert _looks_like_prometheus("") is False
    assert _looks_like_prometheus("# TYPE x gauge") is False  # comentario
    assert _looks_like_prometheus("{}") is False
