"""Testes A3 — OpenTelemetry tracing (3 testes essenciais).

LGPD: nunca PII em spans. Apenas IDs/contadores.
"""
from __future__ import annotations

from app.services.tracing import (
    current_trace_id,
    db_span,
    get_tracer,
    init_tracing,
    llm_span,
)


def test_init_tracing_idempotente() -> None:
    """init_tracing pode ser chamado multiplas vezes sem erro."""
    init_tracing("cartorio-api-test")
    init_tracing("cartorio-api-test")
    tracer = get_tracer("cartorio")
    assert tracer is not None


def test_llm_span_cria_e_finaliza() -> None:
    """llm_span abre e fecha span com atributos de modelo + operacao."""
    init_tracing("cartorio-api-test")
    with llm_span(model="deepseek-v4-flash", operation="chat") as span:
        assert span is not None
        # Dentro do context o span deve estar ativo
        assert current_trace_id() is not None


def test_db_span_cria_e_finaliza() -> None:
    """db_span abre e fecha span com atributos de operacao + tabela."""
    init_tracing("cartorio-api-test")
    with db_span(operation="SELECT", table="audit_log") as span:
        assert span is not None
        assert current_trace_id() is not None


def test_tracing_sem_init_retorna_tracer_valido() -> None:
    """get_tracer funciona sem init (modo NoOp em tests)."""
    tracer = get_tracer("cartorio.noop")
    assert tracer is not None
