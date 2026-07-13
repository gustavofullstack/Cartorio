"""bot_metrics.py — Métricas Prometheus para bots (Telegram/WhatsApp) (T52).

Wrappers leves ao redor de MetricsStore (singleton in-memory) para emitir
métricas específicas de bots:

  - bot_requests_total{channel, status}            counter
  - bot_request_duration_seconds{channel, stage}   histogram (debounce/llm/send)
  - bot_pii_redacted_total{channel, tipo_scrub}    counter (wrapper do pii.py)
  - bot_consent_granted_total{channel, granted}    counter (true/false)
  - bot_fallback_chain_hops_total{channel, from, to} counter

Cardinalidade controlada:
  - channel: 'telegram' | 'whatsapp' (2 valores)
  - status: 'ok' | 'failed' | 'rate_limited' | 'idempotent' (4 valores)
  - stage: 'debounce' | 'llm' | 'send' | 'total' (4 valores)
  - tipo_scrub: 'cpf' | 'rg' | 'telefone' | 'email' | 'cns' | 'cnh' | 'none' (7 valores)
  - granted: 'true' | 'false' (2 valores)
  - from/to: 7 provedores free do fallback chain (14 valores combinados)

Total max de combinacoes: ~700 (saudavel para Prometheus local).

LGPD compliance: nenhum PII em labels (apenas IDs hash).
"""

from __future__ import annotations

import time
from typing import Literal

from app.services.metrics import MetricsStore, store as _global_store


# Use o singleton global do metrics.py para que `/api/v1/metrics/prometheus`
# exponha as métricas de bot junto com as demais (counter/histogram).
store: MetricsStore = _global_store


# ============================================================================
# Type aliases (labels - cardinalidade controlada)
# ============================================================================


ChannelLabel = Literal["telegram", "whatsapp"]
StatusLabel = Literal["ok", "failed", "rate_limited", "idempotent"]
StageLabel = Literal["debounce", "llm", "send", "total"]
TipoScrubLabel = Literal["cpf", "rg", "telefone", "email", "cns", "cnh", "none"]
ConsentLabel = Literal["true", "false"]


# ============================================================================
# Counter helpers
# ============================================================================


def inc_bot_request(channel: ChannelLabel, status: StatusLabel) -> None:
    """Incrementa bot_requests_total{channel, status}."""
    store._make_metric_or_skip_test("bot_requests_total", "counter")
    store.inc_counter(
        "bot_requests_total",
        labels={"channel": channel, "status": status},
    )


def inc_bot_pii_redacted(channel: ChannelLabel, tipo_scrub: TipoScrubLabel) -> None:
    """Incrementa bot_pii_redacted_total{channel, tipo_scrub}."""
    if tipo_scrub == "none":
        return  # nao conta quando nao houve redacao
    store._make_metric_or_skip_test("bot_pii_redacted_total", "counter")
    store.inc_counter(
        "bot_pii_redacted_total",
        labels={"channel": channel, "tipo_scrub": tipo_scrub},
    )


def inc_bot_consent(channel: ChannelLabel, granted: bool) -> None:
    """Incrementa bot_consent_granted_total{channel, granted}."""
    store._make_metric_or_skip_test("bot_consent_granted_total", "counter")
    store.inc_counter(
        "bot_consent_granted_total",
        labels={"channel": channel, "granted": "true" if granted else "false"},
    )


def inc_bot_fallback_hop(channel: ChannelLabel, from_provider: str, to_provider: str) -> None:
    """Incrementa bot_fallback_chain_hops_total{channel, from, to}."""
    store._make_metric_or_skip_test("bot_fallback_chain_hops_total", "counter")
    store.inc_counter(
        "bot_fallback_chain_hops_total",
        labels={"channel": channel, "from": from_provider, "to": to_provider},
    )


# ============================================================================
# Histogram helpers
# ============================================================================


def observe_bot_latency(
    channel: ChannelLabel,
    stage: StageLabel,
    duration_seconds: float,
) -> None:
    """Observa bot_request_duration_seconds{channel, stage}."""
    store._make_metric_or_skip_test("bot_request_duration_seconds", "histogram")
    store.observe_histogram(
        "bot_request_duration_seconds",
        duration_seconds,
        labels={"channel": channel, "stage": stage},
    )


# ============================================================================
# Context manager (facilita medicao total + por stage)
# ============================================================================


class BotStageTimer:
    """Context manager para medir latencia de cada stage do pipeline.

    Uso:
        with BotStageTimer(channel="whatsapp", stage="llm") as t:
            response = await chat_with_fallback(...)
        # t.duration_seconds disponivel apos __exit__

    Tambem emite counter requests_total (status ok/failed) ao sair.
    """

    def __init__(
        self,
        channel: ChannelLabel,
        stage: StageLabel = "total",
        auto_inc_request: bool = True,
    ) -> None:
        self.channel = channel
        self.stage = stage
        self.auto_inc_request = auto_inc_request
        self.start: float = 0.0
        self.duration_seconds: float = 0.0
        self._failed: bool = False

    def __enter__(self) -> "BotStageTimer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.duration_seconds = time.perf_counter() - self.start
        observe_bot_latency(self.channel, self.stage, self.duration_seconds)
        if exc_type is not None:
            self._failed = True
            if self.auto_inc_request:
                inc_bot_request(self.channel, "failed")
        elif self.auto_inc_request and self.stage == "total":
            inc_bot_request(self.channel, "ok")

    def mark_failed(self) -> None:
        """Marca o request como failed (chamado em catch externo)."""
        self._failed = True


# ============================================================================
# Convenience: scrub PII helper que tambem incrementa métrica
# ============================================================================


def scrub_with_metric(text: str, channel: ChannelLabel) -> tuple[str, int]:
    """Aplica PII scrub + incrementa bot_pii_redacted_total{channel, tipo}.

    Args:
        text: texto a fazer scrub.
        channel: 'telegram' ou 'whatsapp'.

    Returns:
        (texto_limpo, total_redacted)
    """
    from app.services.pii import scrub as pii_scrub

    result = pii_scrub(text)
    if result.redaction_count > 0:
        # Incrementa contador por cada tipo detectado (findings eh dict tipo->count)
        for tipo, count in result.findings.items():
            for _ in range(count):
                # tipo ja vem como chave canonica do pii.py (cpf/rg/telefone/email/cns/cnh)
                inc_bot_pii_redacted(channel, tipo)
        # Garantia: se findings vier vazio mas redaction_count > 0 (raro),
        # conta como 'none' para nao perder a observacao.
        if not result.findings:
            inc_bot_pii_redacted(channel, "none")
    return result.text, result.redaction_count


__all__ = [
    "BotStageTimer",
    "ChannelLabel",
    "ConsentLabel",
    "StageLabel",
    "StatusLabel",
    "TipoScrubLabel",
    "inc_bot_consent",
    "inc_bot_fallback_hop",
    "inc_bot_pii_redacted",
    "inc_bot_request",
    "observe_bot_latency",
    "scrub_with_metric",
    "store",
]
