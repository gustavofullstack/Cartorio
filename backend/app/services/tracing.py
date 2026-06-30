"""OpenTelemetry tracing minimal para cartorio API.

Decisao arquitetural (A3 — squad A): usar OTLP apenas se exporter
disponivel. Em dev/test, sem exporter: spans sao criados mas descartados
(noop tracer). Em prod, configurar via env OTEL_EXPORTER_OTLP_ENDPOINT.

Beneficios:
- Spans por request HTTP (via FastAPIInstrumentor).
- Spans por chamada LLM (helper llm_span).
- Spans por query DB (helper db_span).
- trace_id propagado em logs (correlacao com AuditService).

LGPD: nunca colocar PII em span attributes. Apenas IDs hash ou contagens.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_initialized = False


def init_tracing(service_name: str = "cartorio-api") -> None:
    """Inicializa o TracerProvider uma unica vez (idempotente).

    - Se OTEL_EXPORTER_OTLP_ENDPOINT definido: usa BatchSpanProcessor + OTLP.
    - Caso contrario: ConsoleSpanExporter (dev) ou NoOp (test).
    """
    global _initialized
    if _initialized:
        return
    resource = Resource.create({"service.name": service_name, "service.version": "0.6.0"})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        # Lazy import: so carrega OTLP exporter se for usar em prod.
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except ImportError:
            # Exporter opcional: se nao instalado, segue sem export.
            pass
    elif os.getenv("OTEL_CONSOLE_EXPORTER") == "1":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    # Caso sem env: NoOp (spans sao criados mas nao exportados, util em testes).
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str = "cartorio") -> trace.Tracer:
    """Retorna o tracer (sempre disponivel, mesmo sem init)."""
    if not _initialized:
        # Modo silencioso: retorna tracer default (NoOp se nao houver provider).
        return trace.get_tracer(name)
    return trace.get_tracer(name)


@contextmanager
def llm_span(model: str, operation: str) -> Iterator[trace.Span]:
    """Context manager para spans de chamada LLM.

    Atributos seguros (LGPD):
    - llm.model (nao envia prompt/response)
    - llm.operation (chat, completion, embedding)
    """
    tracer = get_tracer("cartorio.llm")
    with tracer.start_as_current_span(f"llm.{operation}") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.operation", operation)
        yield span


@contextmanager
def db_span(operation: str, table: str | None = None) -> Iterator[trace.Span]:
    """Context manager para spans de query DB.

    LGPD: nao inclui WHERE values ou PII. Apenas operation + table.
    """
    tracer = get_tracer("cartorio.db")
    with tracer.start_as_current_span(f"db.{operation}") as span:
        span.set_attribute("db.operation", operation)
        if table:
            span.set_attribute("db.table", table)
        yield span


def current_trace_id() -> str | None:
    """Retorna trace_id hex (32 chars) do span atual, ou None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None
    return f"{ctx.trace_id:032x}"


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """Injeta traceparent em headers HTTP para propagacao W3C."""
    from opentelemetry.propagate import inject

    inject(headers)
    return headers


def extract_trace_context(headers: dict[str, str]) -> Any:
    """Extrai context W3C de headers recebidos (webhook inbound)."""
    from opentelemetry.propagate import extract

    return extract(headers)
