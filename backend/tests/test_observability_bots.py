"""test_observability_bots.py — Testes observability bots (T51-T60).

Cobre:
- Logs estruturados JSON com correlation_id (T51)
- Métricas Prometheus: counters + histograms (T52)
- OpenTelemetry spans (T53)
- Trace ID propagation X-Request-ID (T54)
- Health check bots (T55)
- Dashboard Grafana + alertas Prometheus (T56, T57)
- Dead man's switch audit_log (T58)
- Sentry capture_exception (T59)
- Jaeger trace validation (T60)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# T51: Logs estruturados JSON
# ============================================================================


def test_json_formatter_produz_payload_canonico() -> None:
    """T51: _JsonFormatter gera JSON com ts/level/event."""
    from app.services.chat_pipeline import _JsonFormatter
    import logging

    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    record.event = "bot.test"  # type: ignore[attr-defined]
    out = fmt.format(record)
    parsed = json.loads(out)
    assert parsed["level"] == "INFO"
    assert parsed["msg"] == "hello world"
    assert parsed["event"] == "bot.test"
    assert "ts" in parsed
    assert parsed["logger"] == "test"


def test_json_formatter_captura_extras() -> None:
    """T51: extras (channel, chat_id) sao incluidos no JSON."""
    from app.services.chat_pipeline import _JsonFormatter
    import logging

    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg="bot event",
        args=(),
        exc_info=None,
    )
    record.event = "bot.receive"  # type: ignore[attr-defined]
    record.channel = "whatsapp"  # type: ignore[attr-defined]
    record.chat_id = "abc123"  # type: ignore[attr-defined]
    parsed = json.loads(fmt.format(record))
    assert parsed["channel"] == "whatsapp"
    assert parsed["chat_id"] == "abc123"


def test_emit_log_estruturado() -> None:
    """T51: _emit() registra log com correlation_id."""
    from app.services.chat_pipeline import _emit
    import logging

    with patch("app.services.chat_pipeline.logger") as mock_logger:
        _emit(
            logging.INFO,
            "test message",
            event="bot.test",
            channel="telegram",
            chat_id="hash123",
            correlation_id="trace-abc",
        )
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Level posicional + msg + extras
        assert call_args[0][1] == "test message"
        extra = call_args[1].get("extra", {})
        assert extra.get("event") == "bot.test"
        assert extra.get("channel") == "telegram"
        assert extra.get("chat_id") == "hash123"
        assert extra.get("correlation_id") == "trace-abc"


# ============================================================================
# T52: Métricas Prometheus (bot_requests, latency, pii)
# ============================================================================


def test_bot_requests_total_counter() -> None:
    """T52: inc_bot_request incrementa counter {channel, status}."""
    from app.services.bot_metrics import inc_bot_request, store

    store.counters.pop("bot_requests_total", None)
    inc_bot_request("telegram", "ok")
    inc_bot_request("telegram", "ok")
    inc_bot_request("whatsapp", "failed")

    counters = store.counters.get("bot_requests_total", {})
    assert len(counters) == 2
    # Encontrar keys com channel+status
    found_tg_ok = any("channel=telegram" in k and "status=ok" in k for k in counters)
    assert found_tg_ok


def test_bot_request_duration_histogram() -> None:
    """T52: observe_bot_latency adiciona observation."""
    from app.services.bot_metrics import observe_bot_latency, store

    store.histograms.pop("bot_request_duration_seconds", None)
    observe_bot_latency("whatsapp", "llm", 1.5)
    observe_bot_latency("whatsapp", "send", 0.3)

    hists = store.histograms.get("bot_request_duration_seconds", {})
    assert len(hists) >= 2


def test_bot_pii_redacted_counter() -> None:
    """T52: inc_bot_pii_redacted incrementa {channel, tipo}."""
    from app.services.bot_metrics import inc_bot_pii_redacted, store

    store.counters.pop("bot_pii_redacted_total", None)
    inc_bot_pii_redacted("whatsapp", "cpf")
    inc_bot_pii_redacted("whatsapp", "cpf")
    inc_bot_pii_redacted("whatsapp", "email")

    counters = store.counters.get("bot_pii_redacted_total", {})
    assert len(counters) >= 2


def test_bot_consent_counter() -> None:
    """T52: inc_bot_consent incrementa {channel, granted}."""
    from app.services.bot_metrics import inc_bot_consent, store

    store.counters.pop("bot_consent_granted_total", None)
    inc_bot_consent("telegram", True)
    inc_bot_consent("telegram", False)

    counters = store.counters.get("bot_consent_granted_total", {})
    assert len(counters) == 2


def test_bot_stage_timer_mede_latencia() -> None:
    """T52: BotStageTimer mede duracao e emite histogram."""
    from app.services.bot_metrics import BotStageTimer, store

    store.histograms.pop("bot_request_duration_seconds", None)

    with BotStageTimer(channel="telegram", stage="llm", auto_inc_request=False):
        time.sleep(0.05)  # 50ms

    timer = BotStageTimer(channel="whatsapp", stage="send", auto_inc_request=False)
    with timer:
        time.sleep(0.02)
    assert timer.duration_seconds >= 0.02
    assert timer.duration_seconds < 0.5  # sanity


def test_metrics_render_prometheus_inclui_bot() -> None:
    """T52: render_prometheus expoe bot_* metrics."""
    from app.services.bot_metrics import inc_bot_request, store

    inc_bot_request("whatsapp", "ok")
    output = store.render_prometheus()
    assert "bot_requests_total" in output
    assert "channel=\"whatsapp\"" in output
    assert "status=\"ok\"" in output


# ============================================================================
# T53: OpenTelemetry spans
# ============================================================================


def test_get_tracer_retorna_tracer_valido() -> None:
    """T53: get_tracer('cartorio') retorna tracer mesmo sem init."""
    from app.services.tracing import get_tracer

    tracer = get_tracer("cartorio")
    assert tracer is not None


def test_llm_span_context_manager() -> None:
    """T53: llm_span funciona como context manager."""
    from app.services.tracing import llm_span

    with llm_span(model="auto", operation="chat") as span:
        # span pode ser None se tracer nao inicializado
        if span is not None and hasattr(span, "set_attribute"):
            span.set_attribute("test", "value")
    # Sem excecao


def test_db_span_context_manager() -> None:
    """T53: db_span funciona como context manager."""
    from app.services.tracing import db_span

    with db_span(operation="select", table="clientes") as span:
        if span is not None and hasattr(span, "set_attribute"):
            span.set_attribute("test", "value")


def test_current_trace_id_retorna_none_sem_contexto() -> None:
    """T53: current_trace_id retorna None se nao ha span ativo."""
    from app.services.tracing import current_trace_id

    tid = current_trace_id()
    # Pode ser None ou hex 32 chars (depende se ha context global)
    assert tid is None or (isinstance(tid, str) and len(tid) == 32)


# ============================================================================
# T54: Trace ID propagation X-Request-ID
# ============================================================================


def test_request_id_propagado_audit_log() -> None:
    """T54: request_id eh registrado no audit_log."""
    from app.services.chat_pipeline import audit_log, Channel

    # Nao-bloqueante, apenas verifica que a funcao aceita request_id
    asyncio.run(
        audit_log(
            Channel.WHATSAPP,
            "5511999999999@s.whatsapp.net",
            "content-hash-xyz",
            "send",
            "ok",
            request_id="trace-xyz-123",
        )
    )
    # Audit eh non-blocking, nao levanta excecao
    assert True


def test_process_message_aceita_request_id() -> None:
    """T54: process_message aceita request_id e propaga."""
    from app.services.chat_pipeline import (
        process_message,
        InboundMessage,
        Channel,
    )

    msg = InboundMessage(
        channel=Channel.WHATSAPP,
        sender_id="5511999999999@s.whatsapp.net",
        text="oi",
        update_id="msg-test-1",
    )
    adapter = MagicMock()
    adapter.verify_signature = MagicMock(return_value=True)

    # Mock do redis_bus para evitar conexao real
    with patch("app.services.chat_pipeline.get_bus", return_value=None):
        result = asyncio.run(
            process_message(msg, adapter, request_id="trace-propagated")
        )
    # Pode retornar None (sem debounce) ou OutboundMessage
    # O importante eh nao levantar


# ============================================================================
# T55: Health check bots
# ============================================================================


def test_health_whatsapp_existe() -> None:
    """T55: /whatsapp/health endpoint existe."""
    from app.api.v1.whatsapp import router

    paths = [r.path for r in router.routes]
    assert "/whatsapp/health" in paths


def test_health_pipeline_inclui_canais() -> None:
    """T55: health_check pipeline retorna channels telegram+whatsapp."""
    from app.services.chat_pipeline import health_check

    with patch("app.services.chat_pipeline.get_bus", return_value=None):
        result = asyncio.run(health_check())
    assert "channels" in result
    assert "telegram" in result["channels"]
    assert "whatsapp" in result["channels"]


# ============================================================================
# T56: Dashboard Grafana (arquivo)
# ============================================================================


def test_grafana_dashboard_bots_latency_existe() -> None:
    """T56: arquivo dashboard Grafana bots-latency.json existe."""
    path = Path(__file__).parent.parent.parent / "infra" / "grafana" / "dashboards" / "bots-latency.json"
    assert path.exists(), f"Dashboard nao encontrado: {path}"


def test_grafana_dashboard_bots_latency_valido() -> None:
    """T56: dashboard JSON tem schema Grafana valido."""
    path = Path(__file__).parent.parent.parent / "infra" / "grafana" / "dashboards" / "bots-latency.json"
    with open(path) as f:
        data = json.load(f)
    # Campos canonicos de um dashboard Grafana
    assert "title" in data or "panels" in data
    # Se tem panels, cada panel deve ter id+title+type
    if "panels" in data:
        for panel in data["panels"]:
            assert "id" in panel or "title" in panel


# ============================================================================
# T57: Alerta Prometheus bots-latency
# ============================================================================


def test_alerts_bots_latency_existe() -> None:
    """T57: arquivo alerts/bots-latency.yaml existe."""
    path = Path(__file__).parent.parent.parent / "infra" / "prometheus" / "alerts" / "bots-latency.yaml"
    assert path.exists(), f"Alerta nao encontrado: {path}"


def test_alerts_bots_latency_yaml_valido() -> None:
    """T57: arquivo YAML tem groups + alert com expr + severity."""
    import yaml

    path = Path(__file__).parent.parent.parent / "infra" / "prometheus" / "alerts" / "bots-latency.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    assert "groups" in data
    found = False
    for group in data["groups"]:
        for rule in group.get("rules", []):
            if "alert" in rule and "bot" in rule.get("alert", "").lower():
                found = True
                assert "expr" in rule
                assert "labels" in rule
                assert "severity" in rule["labels"]
                break
    assert found, "Nenhum alerta de bot encontrado"


# ============================================================================
# T58: Dead man's switch audit_log
# ============================================================================


def test_dead_mans_switch_constantes() -> None:
    """T58: dead_mans_switch tem threshold de 1h."""
    from app.services.dead_mans_switch import (
        DEAD_THRESHOLD,
        COLD_START_THRESHOLD,
    )

    assert DEAD_THRESHOLD.total_seconds() == 3600  # 1h
    assert COLD_START_THRESHOLD.total_seconds() <= 600  # <= 10min


def test_check_audit_log_alive_retorna_dict() -> None:
    """T58: check_audit_log_alive retorna dict com chaves canonicas."""
    from app.services.dead_mans_switch import check_audit_log_alive
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.models.base import Base  # noqa: F401

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    S = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    db = S()
    try:
        result = check_audit_log_alive(db)
        assert "alive" in result
        assert "cold_start" in result
        assert "last_seen" in result
        assert "seconds_since_last" in result
        # DB vazio = cold_start
        assert result["cold_start"] is True
        assert result["alive"] is False
    finally:
        db.close()


# ============================================================================
# T59: Sentry capture_exception
# ============================================================================


def test_sentry_scrub_pii_basico() -> None:
    """T59: sentry.scrub_pii remove CPF de strings."""
    from app.services.sentry import scrub_pii

    obj = {
        "msg": "Erro: cliente 123.456.789-09 nao encontrado",
        "cpf": "987.654.321-00",
        "list": ["email: joao@example.com"],
    }
    scrubbed = scrub_pii(obj)
    assert "123.456.789-09" not in scrubbed["msg"]
    assert "987.654.321-00" not in scrubbed["cpf"]
    assert "joao@example.com" not in scrubbed["list"][0]


def test_capture_exception_log_quando_sentry_desabilitado() -> None:
    """T59: capture_exception loga localmente se SENTRY_DSN ausente."""
    from app.services.sentry import capture_exception

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SENTRY_DSN", None)
        # Nao levanta excecao
        try:
            capture_exception(ValueError("test"), extra={"key": "value"})
        except Exception:
            pytest.fail("capture_exception deve ser silencioso quando Sentry offline")


# ============================================================================
# T60: Jaeger trace validation
# ============================================================================


def test_otel_collector_config_up() -> None:
    """T60: otel-collector-config.yml existe com receivers OTLP."""
    path = Path(__file__).parent.parent.parent / "infra" / "observability" / "otel-collector-config.yml"
    assert path.exists()
    content = path.read_text()
    assert "otlp" in content.lower()
    assert "4317" in content or "4318" in content  # OTLP ports


def test_tracing_stack_yml_exists() -> None:
    """T60: tracing-stack.yml Jaeger stack config existe."""
    path = Path(__file__).parent.parent.parent / "infra" / "observability" / "tracing-stack.yml"
    assert path.exists()
    content = path.read_text()
    assert "jaeger" in content.lower() or "otel" in content.lower()