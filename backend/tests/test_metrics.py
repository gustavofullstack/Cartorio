"""Testes do service de metrics Prometheus."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.services.metrics import MetricsStore, render_full_prometheus  # noqa: E402


@pytest.fixture
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager
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
# MetricsStore unit
# ============================================================================


def test_store_counter_basico() -> None:
    s = MetricsStore()
    s.inc_counter("cartorio_x", value=1)
    s.inc_counter("cartorio_x", value=2)
    assert s.counters["cartorio_x"][""] == 3


def test_store_counter_com_labels() -> None:
    s = MetricsStore()
    s.inc_counter("cartorio_x", {"endpoint": "/a", "method": "GET"})
    s.inc_counter("cartorio_x", {"endpoint": "/a", "method": "GET"}, value=5)
    s.inc_counter("cartorio_x", {"endpoint": "/b", "method": "POST"})
    assert s.counters["cartorio_x"]["endpoint=/a|method=GET"] == 6
    assert s.counters["cartorio_x"]["endpoint=/b|method=POST"] == 1


def test_store_histogram_observacoes() -> None:
    s = MetricsStore()
    s.observe_histogram("cartorio_latency", 0.1)
    s.observe_histogram("cartorio_latency", 0.2)
    s.observe_histogram("cartorio_latency", 0.3)
    assert len(s.histograms["cartorio_latency"][""]) == 3
    assert sum(s.histograms["cartorio_latency"][""]) == pytest.approx(0.6)


def test_store_render_prometheus_basico() -> None:
    s = MetricsStore()
    s.inc_counter("cartorio_requests", {"endpoint": "/a"})
    s.set_gauge("cartorio_clientes", 42)
    output = s.render_prometheus()
    assert "# TYPE cartorio_requests counter" in output
    assert 'cartorio_requests{endpoint="/a"} 1' in output
    assert "# TYPE cartorio_clientes gauge" in output
    assert "cartorio_clientes 42.000000" in output
    assert "# TYPE cartorio_uptime_seconds gauge" in output
    assert "cartorio_uptime_seconds" in output


def test_store_render_prometheus_vazio() -> None:
    s = MetricsStore()
    output = s.render_prometheus()
    # Pelo menos uptime
    assert "cartorio_uptime_seconds" in output


# ============================================================================
# Integration com DB
# ============================================================================


def test_collect_db_metrics_retorna_contagens(client) -> None:
    """Snapshot do DB retorna contagens corretas."""
    from app.db import session_scope
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo
    from app.services.metrics import collect_db_metrics

    with session_scope() as db:
        db.add(Cliente(cpf_hash="h1", nome="A", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h2", nome="B", consentimento_lgpd=True))
        db.add(Protocolo(cliente_id=1, numero="X1", tipo="rg", status="aberto", canal_origem="web"))
        db.add(
            Protocolo(cliente_id=1, numero="X2", tipo="rg", status="concluido", canal_origem="web")
        )
        db.commit()

    with session_scope() as db:
        metrics = collect_db_metrics(db)

    assert metrics["clientes_total"] == 2
    assert metrics['protocolos_total{status="aberto"}'] == 1
    assert metrics['protocolos_total{status="concluido"}'] == 1
    assert metrics["audit_chain_length"] >= 0  # pode ter entries de session_scope


def test_endpoint_metrics_retorna_text_prometheus(client) -> None:
    """GET /api/v1/metrics/prometheus retorna text/plain valido."""
    # NAO requer auth (Prometheus scraper roda sem)
    resp = client.get("/api/v1/metrics/prometheus")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    # Formato Prometheus basico
    assert "# TYPE" in body
    assert "cartorio_uptime_seconds" in body


def test_endpoint_metrics_inclui_db_gauge(client) -> None:
    """Endpoint inclui contagens do DB (clientes_total, protocolos_total)."""
    from app.db import session_scope
    from app.models.cliente import Cliente

    with session_scope() as db:
        db.add(Cliente(cpf_hash="h1", nome="A", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h2", nome="B", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h3", nome="C", consentimento_lgpd=True))
        db.commit()

    resp = client.get("/api/v1/metrics/prometheus")
    body = resp.text
    assert "clientes_total 3" in body or "clientes_total 3.0" in body


def test_render_full_prometheus_sem_db() -> None:
    """render_full_prometheus(db=None) ainda funciona (sem DB snapshot)."""
    output = render_full_prometheus(db=None)
    assert "cartorio_uptime_seconds" in output


# ============================================================================
# Endpoint JSON: GET /api/v1/metrics
# ============================================================================
#
# Spec (Sprint 4 / STREAM 1 cartorio-dev 2026-06-24):
# - Retorna JSON estruturado para consumo em N8N workflows (Code node-free).
# - Mesmo modelo de auth do /prometheus (sem auth - usado por scrapers).
# - Reusa collect_db_metrics(db) + adiciona in-process (uptime, http_requests).
# - NUNCA expoe PII (cpf, rg, etc). Apenas contadores e gauges.


def test_endpoint_metrics_json_retorna_200_com_shape(client) -> None:
    """GET /api/v1/metrics retorna 200 + JSON com campos canonicos."""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    body = resp.json()
    # Shape canonico: top-level keys presentes
    assert "clientes_total" in body
    assert "protocolos_total" in body  # dict por status
    assert "audit_chain_length" in body
    assert "uptime_seconds" in body
    assert isinstance(body["protocolos_total"], dict)
    assert isinstance(body["uptime_seconds"], (int, float))
    assert body["uptime_seconds"] >= 0


def test_endpoint_metrics_json_sem_auth(client) -> None:
    """GET /api/v1/metrics NAO exige X-API-Key (igual /prometheus)."""
    # Sem header de auth - deve retornar 200
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    # Header errado tambem nao bloqueia (auth eh opcional)
    resp = client.get("/api/v1/metrics", headers={"X-API-Key": "qualquer"})
    assert resp.status_code == 200


def test_endpoint_metrics_json_com_auth_opcional(client) -> None:
    """GET /api/v1/metrics aceita X-API-Key (forward-compat) mas NAO exige."""
    headers = {"X-API-Key": "a" * 64}
    resp = client.get("/api/v1/metrics", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "uptime_seconds" in body


def test_endpoint_metrics_json_db_vazio(client) -> None:
    """DB sem clientes/protocolos retorna zeros (sem KeyError).

    Nota: audit_chain_length pode ter entries de session_scope (>= 0).
    Clientes_total e protocolos_total devem ser exatamente 0 / {}.
    """
    # Sem adicionar dados - DB vazio
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["clientes_total"] == 0
    assert body["protocolos_total"] == {}  # dict vazio, sem status
    assert body["audit_chain_length"] >= 0  # pode ter entries de session_scope


def test_endpoint_metrics_json_inclui_contagens_db(client) -> None:
    """Endpoint inclui contagens reais do DB (clientes + protocolos)."""
    from app.db import session_scope
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo

    with session_scope() as db:
        db.add(Cliente(cpf_hash="h1", nome="A", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h2", nome="B", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h3", nome="C", consentimento_lgpd=True))
        db.add(Cliente(cpf_hash="h4", nome="D", consentimento_lgpd=True))
        db.add(
            Protocolo(
                cliente_id=1,
                numero="X1",
                tipo="rg",
                status="aberto",
                canal_origem="web",
            )
        )
        db.add(
            Protocolo(
                cliente_id=1,
                numero="X2",
                tipo="rg",
                status="concluido",
                canal_origem="web",
            )
        )
        db.commit()

    resp = client.get("/api/v1/metrics")
    body = resp.json()
    assert body["clientes_total"] == 4
    assert body["protocolos_total"].get("aberto") == 1
    assert body["protocolos_total"].get("concluido") == 1
    assert body["audit_chain_length"] >= 0  # pode ter entries de session_scope


# ============================================================================
# TestMetricsHelpersEdge — FIX 2 (R8 YOLO): cobre linhas 88, 100, 139, 150-151, 163-164, 182-188, 196-197, 206-207, 219-221, 247, 253, 324
# ============================================================================


class TestMetricsHelpersEdge:
    def test_set_gauge_migrates_scalar_to_dict(self) -> None:
        """set_gauge com labels: se gauge eh scalar, migra pra dict preservando o valor."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.set_gauge("test_gauge", 42.0)
        # Agora adicionar com labels -> deve migrar scalar para dict
        s.set_gauge("test_gauge", 99.0, labels={"queue": "evolution"})
        assert isinstance(s.gauges["test_gauge"], dict)
        # Valor antigo (sem labels) foi preservado como key=""
        assert s.gauges["test_gauge"].get("") == 42.0
        # Novo valor com labels
        assert s.gauges["test_gauge"].get("queue=evolution") == 99.0

    def test_make_metric_or_skip_test_invalid_type_raises_valueerror(self) -> None:
        """_make_metric_or_skip_test com metric_type invalido lanca ValueError."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        with pytest.raises(ValueError) as exc_info:
            s._make_metric_or_skip_test("foo", "invalid_type")
        assert "metric_type invalido" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_audit_dead_mans_status_unknown_defaults_to_critical(self) -> None:
        """set_audit_dead_mans_status: status_code fora de {0,1,2} vira 2 (critical)."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        # 99 eh desconhecido -> clamp para 2 (critical, fail-safe)
        s.set_audit_dead_mans_status(99)
        assert s.gauges["audit_dead_mans_status"] == 2.0
        # -1 tambem
        s.set_audit_dead_mans_status(-1)
        assert s.gauges["audit_dead_mans_status"] == 2.0
        # 0 eh healthy
        s.set_audit_dead_mans_status(0)
        assert s.gauges["audit_dead_mans_status"] == 0.0
        # 1 eh warning
        s.set_audit_dead_mans_status(1)
        assert s.gauges["audit_dead_mans_status"] == 1.0

    def test_inc_n8n_wf_execution_increments(self) -> None:
        """inc_n8n_wf_execution incrementa counter n8n_wf_executions_total{wf_name,status}."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.inc_n8n_wf_execution("consulta-emolumento", "success")
        s.inc_n8n_wf_execution("consulta-emolumento", "success")
        s.inc_n8n_wf_execution("consulta-emolumento", "error")
        key_ok = "status=success|wf_name=consulta-emolumento"
        key_err = "status=error|wf_name=consulta-emolumento"
        assert s.counters["n8n_wf_executions_total"][key_ok] == 2
        assert s.counters["n8n_wf_executions_total"][key_err] == 1

    def test_observe_n8n_wf_duration_records(self) -> None:
        """observe_n8n_wf_duration registra histograma n8n_wf_duration_seconds{wf_name}."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.observe_n8n_wf_duration("consulta-emolumento", 0.5)
        s.observe_n8n_wf_duration("consulta-emolumento", 1.2)
        hists = s.histograms["n8n_wf_duration_seconds"]
        key = "wf_name=consulta-emolumento"
        assert len(hists[key]) == 2
        assert sum(hists[key]) == pytest.approx(1.7)

    def test_observe_agent_tokens_records_in_out(self) -> None:
        """observe_agent_tokens registra histograms agent_tokens_in_total e _out_total."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.observe_agent_tokens(tokens_in=100, tokens_out=50, think_tokens=10)
        assert len(s.histograms["agent_tokens_in_total"][""]) == 1
        assert len(s.histograms["agent_tokens_out_total"][""]) == 1
        assert len(s.histograms["agent_think_tokens_total"][""]) == 1
        assert s.histograms["agent_tokens_in_total"][""][0] == 100.0
        assert s.histograms["agent_tokens_out_total"][""][0] == 50.0
        assert s.histograms["agent_think_tokens_total"][""][0] == 10.0

    def test_observe_agent_tokens_no_think(self) -> None:
        """observe_agent_tokens sem think_tokens NAO cria agent_think_tokens_total."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.observe_agent_tokens(tokens_in=5, tokens_out=3)
        assert "agent_tokens_in_total" in s.histograms
        assert "agent_tokens_out_total" in s.histograms
        # Sem think -> NAO cria
        assert "agent_think_tokens_total" not in s.histograms

    def test_observe_agent_latency_records_histogram(self) -> None:
        """observe_agent_latency registra agent_latency_seconds."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.observe_agent_latency(0.42)
        assert s.histograms["agent_latency_seconds"][""] == [0.42]

    def test_inc_agent_requests_total_increments(self) -> None:
        """inc_agent_requests_total incrementa counter agent_requests_total{provider,status}."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.inc_agent_requests_total("opencode_go", "success")
        s.inc_agent_requests_total("opencode_go", "success")
        s.inc_agent_requests_total("openclaw", "rate_limited")
        key_a = "provider=opencode_go|status=success"
        key_b = "provider=openclaw|status=rate_limited"
        assert s.counters["agent_requests_total"][key_a] == 2
        assert s.counters["agent_requests_total"][key_b] == 1

    def test_set_n8n_wf_error_rate_clamps(self) -> None:
        """set_n8n_wf_error_rate: valores fora de [0,1] sao clamped."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.set_n8n_wf_error_rate("foo", 1.5)  # > 1.0 -> clamp 1.0
        assert s.gauges["n8n_wf_error_rate"]["wf_name=foo"] == 1.0
        s.set_n8n_wf_error_rate("bar", -0.5)  # < 0 -> clamp 0.0
        assert s.gauges["n8n_wf_error_rate"]["wf_name=bar"] == 0.0
        s.set_n8n_wf_error_rate("baz", 0.25)
        assert s.gauges["n8n_wf_error_rate"]["wf_name=baz"] == 0.25

    def test_set_backup_last_success_timestamp_none_returns_zero(self) -> None:
        """set_backup_last_success_timestamp(None) -> gauge=0 (cold-start fail-safe)."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.set_backup_last_success_timestamp(None)
        assert s.gauges["backup_last_success_timestamp_seconds"] == 0.0
        # valor numerico valido eh preservado
        s.set_backup_last_success_timestamp(1700000000.5)
        assert s.gauges["backup_last_success_timestamp_seconds"] == 1700000000.5

    def test_labels_key_and_parse_roundtrip(self) -> None:
        """_labels_key e _parse_labels_key sao inversos (modulo dict equality)."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        labels = {"b": "2", "a": "1"}
        key = s._labels_key(labels)
        # Ordem sorted: a=1 vem antes de b=2
        assert key == "a=1|b=2"
        parsed = s._parse_labels_key(key)
        assert parsed == labels

    def test_labels_render_empty(self) -> None:
        """_labels_render com labels=None retorna string vazia."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        assert s._labels_render(None) == ""
        assert s._labels_render({}) == ""

    def test_render_prometheus_gauge_dict_with_labels(self) -> None:
        """render_prometheus expoe gauges com labels em formato key=\"value\"."""
        from app.services.metrics import MetricsStore

        s = MetricsStore()
        s.set_gauge("my_gauge", 12.5, labels={"queue": "evolution"})
        output = s.render_prometheus()
        assert "# TYPE my_gauge gauge" in output
        assert 'my_gauge{queue="evolution"} 12.500000' in output
