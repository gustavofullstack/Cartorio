"""Testes unitários de validação da cobertura das 15+ métricas do Prometheus (Wave 4 S4.T1).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.pii import hash_pii

client = TestClient(app)


def test_prometheus_endpoint_contains_all_15_metrics(db_session) -> None:
    """GET /api/v1/metrics/prometheus -> 200 e deve retornar o formato do Prometheus com as 15+ chaves."""
    # 1. Popula dados de teste para expor status de protocolos
    c = Cliente(
        cpf_hash=hash_pii("111.222.333-44", salt="a" * 32),
        nome="Cliente Metricas",
        whatsapp_number="5534900000000",
        consentimento_lgpd=True,
    )
    db_session.add(c)
    db_session.commit()

    p = Protocolo(
        cliente_id=c.id,
        numero="PROT-METRIC-99",
        status="aberto",
        tipo="Reconhecimento de Firma",
        canal_origem="whatsapp",
    )
    db_session.add(p)
    db_session.commit()

    # 2. Executa a chamada do endpoint
    resp = client.get("/api/v1/metrics/prometheus")
    assert resp.status_code == 200
    text = resp.text

    # Verifica se as 15 métricas críticas estão listadas e tipadas
    expected_metrics = [
        "cartorio_clientes_total",
        "cartorio_lgpd_consent_total",
        "cartorio_audit_chain_length",
        "cartorio_audit_chain_size",
        "cartorio_dlq_pending",
        "cartorio_protocolos_total",
        "cartorio_protocolo_status_total",
        "cartorio_protocolo_total_total",
        "cartorio_emolumento_consultado_total",
        "cartorio_emolumento_erros_total",
        "cartorio_telegram_mensagens_total",
        "cartorio_telegram_erros_total",
        "cartorio_whatsapp_mensagens_total",
        "cartorio_whatsapp_erros_total",
        "cartorio_uptime_seconds",
    ]

    for metric in expected_metrics:
        assert metric in text


def test_metrics_json_contains_new_fields() -> None:
    """GET /api/v1/metrics -> 200 e deve conter os campos agregados de conformidade no JSON."""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    body = resp.json()

    # Verifica campos agregados no JSON
    assert "clientes_total" in body
    assert "audit_chain_length" in body
    assert "audit_chain_size" in body
    assert "lgpd_consent_total" in body
    assert "dlq_pending" in body
    assert "uptime_seconds" in body
    assert "counters" in body
    assert "gauges" in body

    # Valida gauges de pool SQLAlchemy de forma achatada em gauges
    gauges = body["gauges"]
    assert "cartorio_db_pool_size" in gauges
    assert "cartorio_db_pool_utilization_pct" in gauges

    # Verifica se os contadores in-process de cold-start estão no payload
    counters = body["counters"]
    assert "cartorio_emolumento_consultado_total" in counters
    assert "cartorio_emolumento_erros_total" in counters
    assert "cartorio_telegram_mensagens_total" in counters
    assert "cartorio_telegram_erros_total" in counters
    assert "cartorio_whatsapp_mensagens_total" in counters
    assert "cartorio_whatsapp_erros_total" in counters
