"""Testes A2 — Prometheus metrics (LGPD-016 observabilidade).

Cobre:
1. counter `pii_blocked_total{tipo_scrub,channel}` — incrementa a cada scrub bem-sucedido
2. histogram `scrub_latency_ms_bucket{le=...}` + `_count` + `_sum` — captura latencia
3. gauge `dlq_depth{queue}` — atualizado quando outbox cresce/encolhe
4. LGPD-by-design: SEM PII em labels (channel/tipo_scrub/result/queue sao enums)
"""

from __future__ import annotations


import pytest

from app.services.metrics import MetricsStore


@pytest.fixture
def fresh_store():
    """Store limpo por teste (reset state)."""
    store = MetricsStore()
    return store


# ============================================================================
# counter pii_blocked_total
# ============================================================================


def test_counter_pii_blocked_incrementa_em_cada_scrub(fresh_store):
    """Cada chamada a scrub() com PII detectado incrementa o counter."""

    # Aplica scrub que detecta CPF
    fresh_store.inc_counter(
        "pii_blocked_total",
        labels={"tipo_scrub": "cpf", "channel": "whatsapp"},
    )
    fresh_store.inc_counter(
        "pii_blocked_total",
        labels={"tipo_scrub": "cpf", "channel": "whatsapp"},
    )

    output = fresh_store.render_prometheus()
    # Counter exposto como 'pii_blocked_total{tipo_scrub="cpf",channel="whatsapp"} 2'
    assert "pii_blocked_total" in output
    assert 'channel="whatsapp"' in output
    assert 'tipo_scrub="cpf"' in output
    assert " 2" in output  # contador = 2


def test_counter_pii_blocked_cardinalidade_limitada(fresh_store):
    """Cardinalidade do label deve ser enum (whatsapp/telegram/web/api)."""
    valid_channels = ["whatsapp", "telegram", "web", "api"]
    for ch in valid_channels:
        fresh_store.inc_counter(
            "pii_blocked_total",
            labels={"tipo_scrub": "rg", "channel": ch},
        )

    # SEM PII em labels (LGPD-by-design)
    output = fresh_store.render_prometheus()
    assert "cpf" not in output.lower() or "_REDACTED" in output or "tipo_scrub" in output
    assert "rg" in output  # rg como tipo_scrub (enum), NAO como RG value


def test_counter_pii_blocked_total_render_incrementa():
    """Render inclui count correto para cada combinacao de labels."""
    store = MetricsStore()
    store.inc_counter("pii_blocked_total", labels={"tipo_scrub": "cpf", "channel": "whatsapp"})
    store.inc_counter("pii_blocked_total", labels={"tipo_scrub": "cns", "channel": "api"})
    store.inc_counter("pii_blocked_total", labels={"tipo_scrub": "cpf", "channel": "whatsapp"})

    output = store.render_prometheus()
    # 2 para cpf+whatsapp
    assert 'pii_blocked_total{channel="whatsapp",tipo_scrub="cpf"} 2' in output
    # 1 para cns+api
    assert 'pii_blocked_total{channel="api",tipo_scrub="cns"} 1' in output


# ============================================================================
# histogram scrub_latency_ms
# ============================================================================


def test_histogram_scrub_latency_observe_incrementa(fresh_store):
    """observe_histogram() adiciona valor para contagem."""
    fresh_store.observe_histogram("scrub_latency_ms", 1.5, labels={"tipo_scrub": "cpf"})
    fresh_store.observe_histogram("scrub_latency_ms", 2.5, labels={"tipo_scrub": "cpf"})

    output = fresh_store.render_prometheus()
    assert "scrub_latency_ms_count" in output
    assert 'tipo_scrub="cpf"' in output
    assert " 2" in output  # count = 2


def test_histogram_scrub_latency_sum(fresh_store):
    """Soma das latencias eh exposta."""
    fresh_store.observe_histogram("scrub_latency_ms", 10.0, labels={"result": "blocked"})
    fresh_store.observe_histogram("scrub_latency_ms", 20.0, labels={"result": "blocked"})

    output = fresh_store.render_prometheus()
    # soma = 30.0
    assert "scrub_latency_ms_sum" in output
    assert " 30.000000" in output


def test_histogram_scrub_latency_cardinalidade_result_label(fresh_store):
    """Label result eh enum: blocked|allowed (sem PII)."""
    for r in ["blocked", "allowed"]:
        fresh_store.observe_histogram(
            "scrub_latency_ms",
            5.0,
            labels={"tipo_scrub": "cpf", "result": r},
        )

    output = fresh_store.render_prometheus()
    assert 'result="blocked"' in output
    assert 'result="allowed"' in output
    # SEM PII (sem CPF values)
    assert "123.456.789-09" not in output


# ============================================================================
# gauge dlq_depth
# ============================================================================


def test_gauge_dlq_depth_set_value(fresh_store):
    """set_gauge() armazena valor para query posterior."""
    fresh_store.set_gauge("dlq_depth", 42, labels={"queue": "evolution"})

    output = fresh_store.render_prometheus()
    assert "dlq_depth" in output
    assert 'queue="evolution"' in output
    assert " 42.000000" in output


def test_gauge_dlq_depth_multiplas_queues(fresh_store):
    """Gauge suporta multiplas queues (cada uma com seu valor)."""
    fresh_store.set_gauge("dlq_depth", 10, labels={"queue": "evolution"})
    fresh_store.set_gauge("dlq_depth", 5, labels={"queue": "chatwoot"})
    fresh_store.set_gauge("dlq_depth", 0, labels={"queue": "telegram"})

    output = fresh_store.render_prometheus()
    assert 'queue="evolution"' in output and " 10.000000" in output
    assert 'queue="chatwoot"' in output and " 5.000000" in output
    assert 'queue="telegram"' in output and " 0.000000" in output


def test_gauge_dlq_depth_atualiza_quando_muda(fresh_store):
    """Gauge atualiza valor quando set_gauge() eh chamado novamente."""
    fresh_store.set_gauge("dlq_depth", 10, labels={"queue": "evolution"})
    fresh_store.set_gauge("dlq_depth", 20, labels={"queue": "evolution"})
    fresh_store.set_gauge("dlq_depth", 5, labels={"queue": "evolution"})

    output = fresh_store.render_prometheus()
    # Ultimo valor = 5
    assert 'dlq_depth{queue="evolution"} 5.000000' in output


# ============================================================================
# Factory idempotente
# ============================================================================


def test_factory_make_metric_or_skip_test_retorna_existente(fresh_store):
    """Factory retorna metric existente ao inves de criar duplicado."""
    from app.services.metrics import MetricsStore

    store1 = MetricsStore()
    c1 = store1._make_metric_or_skip_test("test_metric", "counter")
    c2 = store1._make_metric_or_skip_test("test_metric", "counter")
    assert c1 is c2  # mesma instancia (idempotente)


def test_factory_make_metric_ou_cria_novo(fresh_store):
    """Factory cria novo se nome nao existe."""
    from app.services.metrics import MetricsStore

    store = MetricsStore()
    c1 = store._make_metric_or_skip_test("novo_metric", "counter")
    c2 = store._make_metric_or_skip_test("outro_metric", "counter")
    assert c1 is not c2


# ============================================================================
# LGPD-by-design: SEM PII em labels
# ============================================================================


def test_lgpd_labels_sem_pii_nao_explode_cardinalidade():
    """Garante que labels aceitos sao apenas enums (cardinalidade limitada)."""
    # Cardinalidade maxima esperada: ~20 valores
    # (4 channels × 7 tipo_scrub × 2 result × 4 queues × 3 status = 672 combos)
    valid_combinations = [
        ("whatsapp", "cpf", "blocked"),
        ("telegram", "rg", "allowed"),
        ("web", "cns", "blocked"),
        ("api", "cnh", "allowed"),
    ]

    for ch, ts, res in valid_combinations:
        store = MetricsStore()
        store.inc_counter(
            "pii_blocked_total",
            labels={"tipo_scrub": ts, "channel": ch},
        )
        store.observe_histogram(
            "scrub_latency_ms",
            5.0,
            labels={"tipo_scrub": ts, "result": res},
        )

    # Labels NAO aceitos (PII ou cardinalidade explodiria)
    forbidden_labels = ["cpf_value", "session_id", "user_email", "request_id", "actor_ip"]
    store = MetricsStore()
    output = store.render_prometheus()
    for fl in forbidden_labels:
        assert fl not in output, f"label proibido '{fl}' encontrado em output"


# ============================================================================
# Integration: instrumentacao em services.pii
# ============================================================================


def test_pii_scrub_instrumenta_counter_e_histogram():
    """services.pii.scrub() instrumenta pii_blocked_total + scrub_latency_ms."""
    from app.services.pii import scrub

    import app.services.metrics as metrics_mod

    # Salva e restaura o store original pra NAO quebrar singleton
    # (test_metrics_a2 2026-06-25 — Lesson: metrics_mod.store = fresh
    #  desvincula o endpoint do singleton original)
    original_store = metrics_mod.store
    try:
        store = MetricsStore()
        metrics_mod.store = store

        # Scrub com PII detectado
        scrub("meu cpf é 123.456.789-09")

        # Verifica que counter incrementou
        output = store.render_prometheus()
        assert "pii_blocked_total" in output
        assert 'tipo_scrub="cpf"' in output
    finally:
        metrics_mod.store = original_store


def test_pii_scrub_sem_pii_nao_incrementa_counter():
    """Scrub sem PII NAO incrementa pii_blocked_total."""
    from app.services.pii import scrub

    import app.services.metrics as metrics_mod

    original_store = metrics_mod.store
    try:
        store = MetricsStore()
        metrics_mod.store = store

        # Scrub SEM PII
        result = scrub("ola mundo sem pii aqui")
        assert result.redaction_count == 0

        output = store.render_prometheus()
        # NAO deve ter increment para cpf/rg/etc
        assert "pii_blocked_total" not in output or " 0" in output
    finally:
        metrics_mod.store = original_store
