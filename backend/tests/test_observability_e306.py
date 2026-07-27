"""E3.06 — Observability gaps: gauge do circuit breaker, webhook auth failures,
gauges de saude WhatsApp (E2.08) e heartbeat do dead-man's switch.

Valida:
- cartorio_llm_circuit_open{provider} 0/1 publicado onde o CB abre/fecha
  (app/integrations/fallback.py::_record_failure/_record_success) e
  re-publicado quando _is_circuit_open confirma abertura no Redis (restart).
- cartorio_webhook_auth_failures_total{channel} nos 401 de webhook
  (Telegram secret + Evolution HMAC).
- cartorio_whatsapp_evolution_service_up / cartorio_whatsapp_session_connected
  alimentados no health check E2.08 (whatsapp_health).
- cartorio_audit_dead_mans_switch_heartbeat (Unix epoch) atualizado a cada
  execucao do check 3-niveis do dead-man's switch.
- prometheus/alerts.yml parseia e referencia SOMENTE metricas reais.

LGPD: labels sao enums canonicos (provider/channel). Testes nao escrevem
valores dinamicos em labels (privacy gate).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import httpx  # noqa: E402
import pytest  # noqa: E402
import yaml  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.services.metrics import MetricsStore  # noqa: E402


# ============================================================================
# Fixtures / helpers
# ============================================================================


@pytest.fixture
def store_isolado(monkeypatch: pytest.MonkeyPatch) -> MetricsStore:
    """Store fresco isolado (mesma estrategia de test_metrics_llm_g8.py)."""
    fresh = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", fresh)
    return fresh


def _counter(s: MetricsStore, metric: str, labels: dict[str, str] | None = None) -> int:
    key = "|".join(f"{k}={v}" for k, v in sorted((labels or {}).items()))
    return s.counters.get(metric, {}).get(key, 0)


def _gauge(s: MetricsStore, metric: str, labels: dict[str, str] | None = None):
    g = s.gauges.get(metric)
    if labels:
        if g is None:
            return None
        key = "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
        assert isinstance(g, dict), f"gauge {metric} nao tem labels: {g!r}"
        return g.get(key)
    return g


# ============================================================================
# Cold-start (Grafana no-data guard)
# ============================================================================


def test_cold_start_series_e306_existem_zeradas() -> None:
    s = MetricsStore()
    assert _counter(s, "cartorio_webhook_auth_failures_total", {"channel": "telegram"}) == 0
    assert _counter(s, "cartorio_webhook_auth_failures_total", {"channel": "whatsapp"}) == 0
    # Heartbeat 0.0 = "nunca rodou" (fail-safe: alerta dispara se DMS nao roda)
    assert _gauge(s, "cartorio_audit_dead_mans_switch_heartbeat") == 0.0
    # Saude WhatsApp desconhecida no boot -> 0 (down, fail-safe)
    assert _gauge(s, "cartorio_whatsapp_evolution_service_up") == 0.0
    assert _gauge(s, "cartorio_whatsapp_session_connected") == 0.0


# ============================================================================
# (a) Gauge do circuit breaker
# ============================================================================


class TestCircuitOpenGauge:
    def test_open_close_transitions(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        s.set_llm_circuit_open("MiniMax_direct", True)
        assert _gauge(s, "cartorio_llm_circuit_open", {"provider": "MiniMax_direct"}) == 1.0
        s.set_llm_circuit_open("MiniMax_direct", False)
        assert _gauge(s, "cartorio_llm_circuit_open", {"provider": "MiniMax_direct"}) == 0.0

    def test_provider_desconhecido_coage_para_unknown(self, store_isolado: MetricsStore) -> None:
        """LGPD/cardinalidade: provider fora da whitelist NUNCA vira label."""
        s = store_isolado
        s.set_llm_circuit_open("provider-injetado-12345", True)
        assert _gauge(s, "cartorio_llm_circuit_open", {"provider": "unknown"}) == 1.0
        assert "provider-injetado-12345" not in str(s.gauges)

    def test_render_contem_gauge_com_label_provider(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        s.set_llm_circuit_open("litellm", True)
        out = s.render_prometheus()
        assert "# TYPE cartorio_llm_circuit_open gauge" in out
        assert 'cartorio_llm_circuit_open{provider="litellm"} 1.000000' in out


class TestCircuitBreakerFallbackIntegration:
    """Gauge atualizado onde o CB abre/fecha de fato (fallback.py + Redis)."""

    @pytest.mark.asyncio
    async def test_record_failure_abre_circuito_e_gauge_vai_para_1(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fakeredis import aioredis as fakeredis_async

        from app.integrations.fallback import _record_failure

        fake = fakeredis_async.FakeRedis()

        class _FakeBus:
            client = fake

        monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: _FakeBus())
        provider = "MiniMax_direct"
        for _ in range(3):  # threshold canonico = 3 (G9.S3.T4)
            await _record_failure(provider, threshold=3, open_time_seconds=300)
        assert await fake.get(f"cb:open:{provider}") == b"1"
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": provider}) == 1.0

    @pytest.mark.asyncio
    async def test_record_success_fecha_circuito_e_gauge_vai_para_0(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fakeredis import aioredis as fakeredis_async

        from app.integrations.fallback import _record_failure, _record_success

        fake = fakeredis_async.FakeRedis()

        class _FakeBus:
            client = fake

        monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: _FakeBus())
        provider = "litellm"
        for _ in range(3):
            await _record_failure(provider, threshold=3, open_time_seconds=300)
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": provider}) == 1.0
        await _record_success(provider)
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": provider}) == 0.0

    @pytest.mark.asyncio
    async def test_is_circuit_open_republica_gauge_apos_restart(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Restart do processo: gauge in-memory se perde, CB vive no Redis.

        O proximo _is_circuit_open que confirma abertura re-publica o gauge=1.
        """
        from fakeredis import aioredis as fakeredis_async

        from app.integrations.fallback import _is_circuit_open

        fake = fakeredis_async.FakeRedis()
        provider = "opencode_free_1"
        await fake.set(f"cb:open:{provider}", "1")

        class _FakeBus:
            client = fake

        monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: _FakeBus())
        # Store fresco: simula restart (gauge ausente)
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": provider}) is None
        assert await _is_circuit_open(provider) is True
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": provider}) == 1.0

    @pytest.mark.asyncio
    async def test_is_circuit_open_falso_nao_publica_zero(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Redis down e fail-open: NAO pode mascarar circuito aberto com 0."""
        from app.integrations.fallback import _is_circuit_open

        monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: None)
        store_isolado.set_llm_circuit_open("openclaw", True)
        assert await _is_circuit_open("openclaw") is False  # fail-open
        # Gauge preservado (nao foi zerado pelo caminho fail-open)
        assert _gauge(store_isolado, "cartorio_llm_circuit_open", {"provider": "openclaw"}) == 1.0


# ============================================================================
# (b) Webhook auth failures
# ============================================================================


class TestWebhookAuthFailures:
    def test_incremento_por_canal(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        s.inc_webhook_auth_failures("telegram")
        s.inc_webhook_auth_failures("telegram")
        s.inc_webhook_auth_failures("whatsapp")
        assert _counter(s, "cartorio_webhook_auth_failures_total", {"channel": "telegram"}) == 2
        assert _counter(s, "cartorio_webhook_auth_failures_total", {"channel": "whatsapp"}) == 1

    def test_canal_desconhecido_coage_para_unknown(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        s.inc_webhook_auth_failures("5511999999999")  # tentativa de PII/dinamico
        assert _counter(s, "cartorio_webhook_auth_failures_total", {"channel": "unknown"}) == 1
        assert "5511999999999" not in s.render_prometheus()

    def test_telegram_secret_401_conta_auth_failure(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ambos os pontos de 401 de _verify_telegram_secret contam."""
        import app.api.v1.telegram as tg

        monkeypatch.setattr(tg, "TELEGRAM_WEBHOOK_SECRET", "segredo-teste")
        base = _counter(
            store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "telegram"}
        )
        # (1) header ausente
        with pytest.raises(HTTPException) as exc1:
            tg._verify_telegram_secret(None)
        assert exc1.value.status_code == 401
        # (2) header invalido
        with pytest.raises(HTTPException) as exc2:
            tg._verify_telegram_secret("token-errado")
        assert exc2.value.status_code == 401
        assert (
            _counter(store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "telegram"})
            == base + 2
        )
        # Caminho feliz NAO conta
        tg._verify_telegram_secret("segredo-teste")
        assert (
            _counter(store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "telegram"})
            == base + 2
        )

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_401_conta_auth_failure(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HMAC Evolution invalido -> 401 fail-closed + counter."""
        from app.api.v1 import whatsapp

        monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "true")
        monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "segredo-evolution-teste")

        adapter = MagicMock()
        adapter.verify_signature = AsyncMock(return_value=False)
        monkeypatch.setattr(whatsapp, "get_adapter", lambda: adapter)

        req = MagicMock()
        req.body = AsyncMock(return_value=b"{}")
        req.headers = {}
        base = _counter(
            store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "whatsapp"}
        )
        with pytest.raises(HTTPException) as exc:
            await whatsapp.whatsapp_webhook(req, MagicMock(), {}, MagicMock())
        assert exc.value.status_code == 401
        assert (
            _counter(store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "whatsapp"})
            == base + 1
        )


# ============================================================================
# (c) Gauges de saude WhatsApp (health E2.08)
# ============================================================================


class _FakeEvoClient:
    def __init__(self, response: httpx.Response | None = None, exc: Exception | None = None):
        self._response = response
        self._exc = exc

    async def get(self, url: str, **kwargs) -> httpx.Response:
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


class _FakeEvoAdapter:
    base_url = "https://evolution.example"
    instance = "cartorio-2notas"

    def __init__(self, client: _FakeEvoClient):
        self._client = client

    async def _get_client(self) -> _FakeEvoClient:
        return self._client


async def _fake_pipeline_ok() -> dict:
    return {"status": "ok"}


class TestWhatsappHealthGauges:
    def _mount(self, monkeypatch: pytest.MonkeyPatch, client: _FakeEvoClient) -> None:
        from app.api.v1 import whatsapp

        monkeypatch.setattr(whatsapp, "get_adapter", lambda: _FakeEvoAdapter(client))
        monkeypatch.setattr(whatsapp, "pipeline_health", _fake_pipeline_ok)

    @pytest.mark.asyncio
    async def test_sessao_aberta_gauges_1_1(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.api.v1 import whatsapp

        self._mount(
            monkeypatch,
            _FakeEvoClient(response=httpx.Response(200, json={"instance": {"state": "open"}})),
        )
        out = await whatsapp.whatsapp_health()
        assert out["status"] == "ok"
        assert _gauge(store_isolado, "cartorio_whatsapp_evolution_service_up") == 1.0
        assert _gauge(store_isolado, "cartorio_whatsapp_session_connected") == 1.0

    @pytest.mark.asyncio
    async def test_api_online_sessao_fechada_gauges_1_0(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lesson 260 (E2.08): evolution online NAO implica sessao conectada."""
        from app.api.v1 import whatsapp

        self._mount(
            monkeypatch,
            _FakeEvoClient(response=httpx.Response(200, json={"instance": {"state": "close"}})),
        )
        out = await whatsapp.whatsapp_health()
        assert out["status"] == "degraded"
        assert _gauge(store_isolado, "cartorio_whatsapp_evolution_service_up") == 1.0
        assert _gauge(store_isolado, "cartorio_whatsapp_session_connected") == 0.0

    @pytest.mark.asyncio
    async def test_evolution_offline_gauges_0_0(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.api.v1 import whatsapp

        self._mount(monkeypatch, _FakeEvoClient(exc=httpx.ConnectError("evo down")))
        out = await whatsapp.whatsapp_health()
        assert out["evolution_api"] == "offline"
        assert _gauge(store_isolado, "cartorio_whatsapp_evolution_service_up") == 0.0
        assert _gauge(store_isolado, "cartorio_whatsapp_session_connected") == 0.0


# ============================================================================
# (d) Heartbeat do dead-man's switch
# ============================================================================


class TestDeadMansHeartbeat:
    def test_heartbeat_explicito(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        s.set_audit_dead_mans_heartbeat(1_700_000_000.0)
        assert _gauge(s, "cartorio_audit_dead_mans_switch_heartbeat") == 1_700_000_000.0

    def test_heartbeat_default_e_agora(self, store_isolado: MetricsStore) -> None:
        s = store_isolado
        before = time.time()
        s.set_audit_dead_mans_heartbeat()
        after = time.time()
        ts = _gauge(s, "cartorio_audit_dead_mans_switch_heartbeat")
        assert ts is not None
        assert before <= ts <= after

    def test_check_3lvl_atualiza_heartbeat_e_status(
        self, store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integracao: run do check (cron/loop) prova scheduler vivo."""
        from app.jobs import dead_mans_switch as dms

        fake_health = dms.AuditHealth(
            status=dms.HealthStatus.HEALTHY,
            last_entry_at=None,
            last_entry_age_minutes=None,
            threshold_minutes=60,
        )
        monkeypatch.setattr(dms, "check_audit_log_freshness", lambda *a, **k: fake_health)
        before = time.time()
        result = dms.check_audit_log_freshness_3lvl(MagicMock(), threshold_minutes=60)
        assert result.status.value == "healthy"
        ts = _gauge(store_isolado, "cartorio_audit_dead_mans_switch_heartbeat")
        assert ts is not None
        assert before <= ts <= time.time()
        # Gauge 3-niveis pre-existente preservado (0=healthy)
        assert _gauge(store_isolado, "audit_dead_mans_status") == 0.0


# ============================================================================
# Render + alerts.yml
# ============================================================================


def test_render_prometheus_inclui_todas_series_e306(store_isolado: MetricsStore) -> None:
    s = store_isolado
    s.set_llm_circuit_open("openclaw", True)
    s.inc_webhook_auth_failures("telegram")
    s.set_whatsapp_health(True, False)
    s.set_audit_dead_mans_heartbeat(1_700_000_000.0)
    out = s.render_prometheus()
    for expected in (
        'cartorio_llm_circuit_open{provider="openclaw"} 1.000000',
        'cartorio_webhook_auth_failures_total{channel="telegram"} 1',
        "cartorio_whatsapp_evolution_service_up 1.000000",
        "cartorio_whatsapp_session_connected 0.000000",
        "cartorio_audit_dead_mans_switch_heartbeat 1700000000.000000",
    ):
        assert expected in out, f"serie ausente no render: {expected}"


class TestAlertsYml:
    """alerts.yml parseia e referencia SOMENTE metricas implementadas."""

    ALERTS_PATH = Path(__file__).resolve().parents[2] / "prometheus" / "alerts.yml"

    # Metricas reais referenciaveis (implementadas em app/services/metrics.py
    # e instrumentadas nos call sites). time() eh funcao PromQL, nao metrica.
    KNOWN_METRICS = {
        "cartorio_llm_circuit_open",
        "cartorio_llm_degraded_total",
        "cartorio_llm_calls_total",
        "dlq_depth",
        "cartorio_webhook_auth_failures_total",
        "cartorio_whatsapp_evolution_service_up",
        "cartorio_whatsapp_session_connected",
        "cartorio_audit_dead_mans_switch_heartbeat",
        "telegram_webhook_total",
        "telegram_response_sent_total",
        "telegram_debounce_scheduled_total",
    }

    EXPECTED_ALERTS = {
        "LLMCircuitOpen",
        "LLMAllProvidersDegraded",
        "DLQGrowing",
        "WebhookAuthFailures",
        "WhatsAppSessionDisconnected",
        "DeadMansSwitch",
        "TelegramWebhookAuthSpike",
        "TelegramResponseSentZero",
        "TelegramLLMFallbackExhausted",
    }

    def _load(self) -> dict:
        with open(self.ALERTS_PATH) as f:
            return yaml.safe_load(f)

    def test_yaml_parseia_e_tem_os_9_alertas(self) -> None:
        doc = self._load()
        names = {r["alert"] for g in doc["groups"] for r in g["rules"]}
        assert names == self.EXPECTED_ALERTS

    def test_exprs_referenciam_apenas_metricas_reais(self) -> None:
        import re

        doc = self._load()
        for group in doc["groups"]:
            for rule in group["rules"]:
                expr = rule["expr"]
                # tokens metricos: identificadores seguidos de { ou operador
                candidates = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*(?=\{)", expr))
                # strip label matchers {result="401"} antes do regex de operador,
                # senao a chave da label ('result') e capturada como metrica
                expr_sem_labels = re.sub(r"\{[^}]*\}", "", expr)
                candidates |= set(
                    re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*(?=\s*[><=!])", expr_sem_labels)
                )
                candidates |= set(re.findall(r"(?:rate|increase)\(([a-zA-Z_][a-zA-Z0-9_]*)", expr))
                unknown = candidates - self.KNOWN_METRICS - {"time"}
                assert not unknown, (
                    f"alert {rule['alert']}: metricas desconhecidas {unknown} em {expr!r}"
                )

    def test_exprs_canonicas_e306(self) -> None:
        doc = self._load()
        exprs = {r["alert"]: r["expr"] for g in doc["groups"] for r in g["rules"]}
        assert exprs["LLMCircuitOpen"] == "cartorio_llm_circuit_open == 1"
        assert "cartorio_webhook_auth_failures_total" in exprs["WebhookAuthFailures"]
        assert "cartorio_whatsapp_evolution_service_up == 1" in exprs["WhatsAppSessionDisconnected"]
        assert "cartorio_whatsapp_session_connected == 0" in exprs["WhatsAppSessionDisconnected"]
        assert "cartorio_audit_dead_mans_switch_heartbeat > 900" in exprs["DeadMansSwitch"]
        assert 'telegram_webhook_total{result="401"}' in exprs["TelegramWebhookAuthSpike"]
        assert "telegram_response_sent_total" in exprs["TelegramResponseSentZero"]
        assert 'status="success"' in exprs["TelegramLLMFallbackExhausted"]
