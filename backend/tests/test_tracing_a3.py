"""Testes A3 — OpenTelemetry tracing (essenciais + borda).

LGPD: nunca PII em spans. Apenas IDs/contadores.

Cobertura:
- init_tracing idempotente
- init_tracing com console exporter
- init_tracing com OTLP endpoint (sem import do exporter)
- llm_span cria span (context manager)
- db_span cria span (context manager)
- current_trace_id com e sem span ativo
- inject_trace_context
- extract_trace_context
- get_tracer sem init
"""

from __future__ import annotations

import os
from unittest.mock import patch

from app.services.tracing import (
    current_trace_id,
    db_span,
    extract_trace_context,
    get_tracer,
    init_tracing,
    inject_trace_context,
    llm_span,
)


def teardown_function() -> None:
    """Reseta _initialized global apos cada teste."""
    import app.services.tracing as mod

    mod._initialized = False


# ─── Init ───────────────────────────────────────────────────────────────


def test_init_tracing_idempotente() -> None:
    """init_tracing pode ser chamado multiplas vezes sem erro."""
    init_tracing("cartorio-api-test")
    init_tracing("cartorio-api-test")
    tracer = get_tracer("cartorio")
    assert tracer is not None


def test_init_tracing_sem_env_console_exporter() -> None:
    """init_tracing com OTEL_CONSOLE_EXPORTER=1 ativa console exporter."""
    with patch.dict(os.environ, {"OTEL_CONSOLE_EXPORTER": "1"}, clear=True):
        init_tracing("cartorio-test")
        tracer = get_tracer("cartorio")
        assert tracer is not None


def test_init_tracing_otlp_sem_exporter_ok() -> None:
    """init_tracing com OTEL_ENDPOINT mas sem OTLP exporter nao quebra."""
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel:4317"}, clear=True):
        init_tracing("cartorio-test")
        tracer = get_tracer("cartorio")
        assert tracer is not None


# ─── Spans ──────────────────────────────────────────────────────────────


def test_llm_span_cria_e_finaliza() -> None:
    """llm_span abre e fecha span com atributos de modelo + operacao."""
    init_tracing("cartorio-api-test")
    with llm_span(model="deepseek-v4-flash", operation="chat") as span:
        assert span is not None
        assert current_trace_id() is not None


def test_db_span_cria_e_finaliza() -> None:
    """db_span abre e fecha span com atributos de operacao + tabela."""
    init_tracing("cartorio-api-test")
    with db_span(operation="SELECT", table="audit_log") as span:
        assert span is not None
        assert current_trace_id() is not None


def test_db_span_sem_tabela() -> None:
    """db_span funciona sem parametro table."""
    init_tracing("cartorio-api-test")
    with db_span(operation="BEGIN") as span:
        assert span is not None
        assert current_trace_id() is not None


# ─── current_trace_id ───────────────────────────────────────────────────


def test_tracing_sem_init_retorna_tracer_valido() -> None:
    """get_tracer funciona sem init (modo NoOp em tests)."""
    tracer = get_tracer("cartorio.noop")
    assert tracer is not None


def test_current_trace_id_sem_span_retorna_none() -> None:
    """current_trace_id retorna None quando nao ha span ativo."""
    tid = current_trace_id()
    assert tid is None


def test_current_trace_id_com_span_retorna_hex() -> None:
    """current_trace_id retorna string hex 32 chars com span ativo."""
    init_tracing("cartorio-test")
    with db_span(operation="SELECT", table="test") as _:
        tid = current_trace_id()
        assert tid is not None
        assert len(tid) == 32
        assert all(c in "0123456789abcdef" for c in tid)


# ─── Context propagation ───────────────────────────────────────────────


def test_inject_trace_context_adiciona_traceparent() -> None:
    """inject_trace_context adiciona header traceparent."""
    init_tracing("cartorio-test")
    with db_span(operation="SELECT", table="test") as _:
        headers: dict[str, str] = {"content-type": "application/json"}
        result = inject_trace_context(headers)
        assert "traceparent" in result
        assert result["traceparent"].startswith("00-")


def test_extract_trace_context_recebe_headers() -> None:
    """extract_trace_context retorna um objeto de contexto valido."""
    init_tracing("cartorio-test")
    headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
    ctx = extract_trace_context(headers)
    assert ctx is not None
