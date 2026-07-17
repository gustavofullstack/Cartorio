"""G7 Wave 18 — rate-limit metrics + telegram think strip + DLQ policy.

Modified by Gustavo Almeida — G7 Wave 18.
"""

from __future__ import annotations

from app.api.v1.telegram import format_bot_text
from app.services.metrics import MetricsStore


def test_inc_rate_limit_total_layers() -> None:
    store = MetricsStore()
    store.inc_rate_limit_total(layer="ddos", tier="none")
    store.inc_rate_limit_total(layer="sliding", tier="none")
    store.inc_rate_limit_total(layer="tier", tier="n8n")
    rendered = store.render_prometheus()
    assert "cartorio_rate_limit_total" in rendered
    assert 'layer="ddos"' in rendered
    assert 'tier="n8n"' in rendered


def test_format_bot_text_strips_think_and_reasoning() -> None:
    raw = "Ola <think>segredo interno</think> mundo <reasoning>raciocinio</reasoning> fim"
    out = format_bot_text(raw)
    assert "segredo" not in out
    assert "raciocinio" not in out
    assert "think" not in out.lower()
    assert "Ola" in out or "ola" in out.lower() or "mundo" in out
    assert "fim" in out


def test_format_bot_text_keeps_plain_pt() -> None:
    assert "emolumento" in format_bot_text("Consulta de emolumento MG 2026").lower()


def test_dlq_backoff_schedule_matches_module() -> None:
    from app.services.dlq import BACKOFF_SCHEDULE_SECONDS, MAX_ATTEMPTS

    assert MAX_ATTEMPTS == 3
    assert BACKOFF_SCHEDULE_SECONDS == (60, 300, 900)
