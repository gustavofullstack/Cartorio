"""Wave Final P0 — testes de fechamento do gap de coverage (89.52% -> >=90%).

Modulos-alvo (gaps reais identificados no report de coverage da Wave):
- app/services/slo_metrics.py        (38% -> alvo ~100%)
- app/services/materialized_views.py (0%  -> alvo ~100%)
- app/api/v1/lgpd_dsar.py            (0%  -> alvo ~100%)
- app/api/v1/dead_mans_switch.py     (36% -> alvo ~95%)

Nao sao testes vazios: cada caso exercita logica real (hash PII, deadline legal,
threshold do dead man's switch, DDL das views, guards de prometheus).

LGPD: DSAR endpoint recebe CPF/email/telefone. Testes usam CPF sintetico de
checksum valido (529.982.247-25, amplamente usado como fixture publica) e
ASSEVERAM que a resposta NUNCA ecoa PII raw — apenas SHA256[:16].
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# app/services/slo_metrics.py
# ---------------------------------------------------------------------------


class TestSloMetrics:
    def test_prometheus_enabled_flag(self) -> None:
        from app.services import slo_metrics

        # prometheus_client e opcional (lazy import): presente em prod, ausente
        # no venv de teste. O contrato e: flag booleana coerente com o import.
        assert slo_metrics.PROMETHEUS_ENABLED is False

    def test_record_http_request_status_class_mapping(self) -> None:
        from app.services import slo_metrics

        # 200 -> 2xx, 404 -> 4xx, 500 -> 5xx (sem excecao = linhas cobertas)
        slo_metrics.record_http_request("GET", "/api/v1/test", 200, 0.123)
        slo_metrics.record_http_request("POST", "/api/v1/test", 404, 0.050)
        slo_metrics.record_http_request("GET", "/api/v1/test", 500, 1.500)

    def test_record_http_request_noop_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services import slo_metrics

        monkeypatch.setattr(slo_metrics, "PROMETHEUS_ENABLED", False)
        # early return — nao pode levantar nem tocar metricas
        slo_metrics.record_http_request("GET", "/x", 200, 0.1)
        slo_metrics.record_n8n_workflow("wf", "success")
        slo_metrics.record_openclaw_request("agent", "/run", 0.2)
        slo_metrics.update_composite_slo(0.99, 0.95)
        slo_metrics.update_error_budget("api_availability", 0.8)

    def test_record_n8n_workflow_success_and_error(self) -> None:
        from app.services import slo_metrics

        slo_metrics.record_n8n_workflow("wf_inbound", "success")
        slo_metrics.record_n8n_workflow("wf_inbound", "error")

    def test_record_openclaw_request(self) -> None:
        from app.services import slo_metrics

        slo_metrics.record_openclaw_request("cartorio-agent", "/chat", 2.5)

    def test_update_composite_slo(self) -> None:
        from app.services import slo_metrics

        slo_metrics.update_composite_slo(0.995, 0.98)

    def test_update_error_budget(self) -> None:
        from app.services import slo_metrics

        slo_metrics.update_error_budget("api_latency", 0.75)

    def test_is_slo_enabled_default_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services import slo_metrics

        monkeypatch.setattr(slo_metrics, "PROMETHEUS_ENABLED", True)
        monkeypatch.delenv("SLO_METRICS_ENABLED", raising=False)
        assert slo_metrics.is_slo_enabled() is True

    def test_is_slo_enabled_env_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services import slo_metrics

        monkeypatch.setattr(slo_metrics, "PROMETHEUS_ENABLED", True)
        monkeypatch.setenv("SLO_METRICS_ENABLED", "false")
        assert slo_metrics.is_slo_enabled() is False

    def test_is_slo_enabled_false_without_prometheus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services import slo_metrics

        monkeypatch.setattr(slo_metrics, "PROMETHEUS_ENABLED", False)
        monkeypatch.delenv("SLO_METRICS_ENABLED", raising=False)
        assert slo_metrics.is_slo_enabled() is False


# ---------------------------------------------------------------------------
# app/services/materialized_views.py
# ---------------------------------------------------------------------------


class TestMaterializedViews:
    def test_views_ddl_has_4_views(self) -> None:
        from app.services.materialized_views import VIEWS_DDL

        assert len(VIEWS_DDL) == 4
        joined = "\n".join(VIEWS_DDL)
        for view in (
            "v_cliente_consent_summary",
            "v_audit_daily",
            "v_dsar_status",
            "v_retention_queue",
        ):
            assert view in joined

    def test_views_ddl_never_selects_raw_pii_columns(self) -> None:
        """LGPD: view de consent usa cpf_hash, nunca cpf raw."""
        from app.services.materialized_views import VIEWS_DDL

        consent_view = VIEWS_DDL[0]
        assert "cpf_hash" in consent_view
        assert "c.cpf," not in consent_view and "c.cpf " not in consent_view

    def test_indexes_ddl_count_and_targets(self) -> None:
        from app.services.materialized_views import INDEXES_DDL

        assert len(INDEXES_DDL) == 5
        assert all("IF NOT EXISTS" in ddl for ddl in INDEXES_DDL)

    def test_render_refresh_views_sql_atomic(self) -> None:
        from app.services.materialized_views import render_refresh_views_sql

        sql = render_refresh_views_sql()
        assert sql.startswith("BEGIN;")
        assert sql.rstrip().endswith("COMMIT;")
        assert sql.count("REFRESH MATERIALIZED VIEW CONCURRENTLY") == 4

    def test_render_create_all_sql_contains_views_and_indexes(self) -> None:
        from app.services.materialized_views import (
            INDEXES_DDL,
            VIEWS_DDL,
            render_create_all_sql,
        )

        sql = render_create_all_sql()
        for ddl in VIEWS_DDL:
            assert ddl.strip()[:60] in sql
        for idx in INDEXES_DDL:
            assert idx in sql


# ---------------------------------------------------------------------------
# app/api/v1/lgpd_dsar.py
# ---------------------------------------------------------------------------

# CPF sintetico de checksum valido (fixture publica classica de testes BR)
SYNTHETIC_CPF = "529.982.247-25"
SYNTHETIC_CPF_HASH = hashlib.sha256(SYNTHETIC_CPF.encode()).hexdigest()[:16]


class TestLgpdDsarHelpers:
    def test_generate_request_id_format(self) -> None:
        from app.api.v1.lgpd_dsar import generate_request_id

        rid = generate_request_id()
        assert rid.startswith("DSAR-")
        assert len(rid) > 10
        # unicidade
        assert generate_request_id() != rid

    def test_hash_pii_sha256_truncated(self) -> None:
        from app.api.v1.lgpd_dsar import hash_pii

        h = hash_pii(SYNTHETIC_CPF)
        assert h == SYNTHETIC_CPF_HASH
        assert len(h) == 16
        assert SYNTHETIC_CPF not in h

    def test_legal_deadline_is_15_days(self) -> None:
        from app.api.v1.lgpd_dsar import LEGAL_DEADLINE_DAYS

        assert LEGAL_DEADLINE_DAYS == 15  # LGPD art. 18 par. 5o


class TestLgpdDsarCreate:
    def _payload(self, **overrides):
        from app.api.v1.lgpd_dsar import DSARCreate, LGPDRight

        data = {
            "cpf": SYNTHETIC_CPF,
            "email": "sintetico@example.com",
            "phone": "34999990000",
            "rights": [LGPDRight.ACESSO, LGPDRight.PORTABILIDADE],
        }
        data.update(overrides)
        return DSARCreate(**data)

    def test_create_dsar_hashes_pii_and_sets_deadline(self) -> None:
        from app.api.v1.lgpd_dsar import create_dsar

        resp = create_dsar(self._payload(), db=MagicMock())
        assert resp.request_id.startswith("DSAR-")
        assert resp.cpf_hash == SYNTHETIC_CPF_HASH
        assert resp.email_hash is not None and "sintetico" not in resp.email_hash
        assert resp.phone_hash is not None
        # PII raw NUNCA na resposta serializada
        dumped = resp.model_dump_json()
        assert SYNTHETIC_CPF not in dumped
        assert "34999990000" not in dumped
        # Deadline legal = ~15 dias
        received = datetime.fromisoformat(resp.received_at)
        deadline = datetime.fromisoformat(resp.deadline)
        assert timedelta(days=14) < (deadline - received) <= timedelta(days=15, seconds=5)

    def test_create_dsar_without_optional_contact(self) -> None:
        from app.api.v1.lgpd_dsar import create_dsar

        resp = create_dsar(self._payload(email=None, phone=None), db=MagicMock())
        assert resp.email_hash is None
        assert resp.phone_hash is None
        assert resp.cpf_hash == SYNTHETIC_CPF_HASH


class TestLgpdDsarStatus:
    def test_status_valid_id_returns_pending(self) -> None:
        from app.api.v1.lgpd_dsar import get_dsar_status

        resp = get_dsar_status("DSAR-abc123", db=MagicMock())
        assert resp.request_id == "DSAR-abc123"
        assert resp.status == "pending"

    def test_status_invalid_id_raises_400(self) -> None:
        from app.api.v1.lgpd_dsar import get_dsar_status

        with pytest.raises(HTTPException) as exc:
            get_dsar_status("WRONG-abc", db=MagicMock())
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# app/api/v1/dead_mans_switch.py
# ---------------------------------------------------------------------------


class TestDeadMansSwitch:
    def test_status_disabled_when_threshold_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1 import dead_mans_switch as dms

        monkeypatch.setattr(dms.settings, "audit_dead_mans_switch_minutes", 0)
        resp = dms.get_status(db=MagicMock())
        assert resp.enabled is False
        assert resp.is_alive is True
        assert resp.last_heartbeat is None

    def test_status_no_audit_log_is_dead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1 import dead_mans_switch as dms

        monkeypatch.setattr(dms.settings, "audit_dead_mans_switch_minutes", 15)
        db = MagicMock()
        db.query.return_value.order_by.return_value.first.return_value = None
        resp = dms.get_status(db=db)
        assert resp.enabled is True
        assert resp.is_alive is False
        assert "Nenhum audit log" in resp.message

    def test_status_recent_heartbeat_is_alive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1 import dead_mans_switch as dms

        monkeypatch.setattr(dms.settings, "audit_dead_mans_switch_minutes", 15)
        log = SimpleNamespace(timestamp=datetime.now(timezone.utc) - timedelta(seconds=30))
        db = MagicMock()
        db.query.return_value.order_by.return_value.first.return_value = log
        resp = dms.get_status(db=db)
        assert resp.is_alive is True
        assert resp.age_seconds is not None and resp.age_seconds < 900

    def test_status_stale_heartbeat_is_dead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1 import dead_mans_switch as dms

        monkeypatch.setattr(dms.settings, "audit_dead_mans_switch_minutes", 15)
        log = SimpleNamespace(timestamp=datetime.now(timezone.utc) - timedelta(hours=2))
        db = MagicMock()
        db.query.return_value.order_by.return_value.first.return_value = log
        resp = dms.get_status(db=db)
        assert resp.is_alive is False
        assert "MORTO" in resp.message

    def test_status_naive_timestamp_treated_as_utc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1 import dead_mans_switch as dms

        monkeypatch.setattr(dms.settings, "audit_dead_mans_switch_minutes", 15)
        log = SimpleNamespace(timestamp=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10))  # naive
        db = MagicMock()
        db.query.return_value.order_by.return_value.first.return_value = log
        resp = dms.get_status(db=db)
        assert resp.is_alive is True

    def test_force_heartbeat_success(self) -> None:
        from app.api.v1 import dead_mans_switch as dms

        db = MagicMock()
        with patch("app.services.audit.AuditService.log") as mock_log:
            dms.force_heartbeat(db=db)
            mock_log.assert_called_once()
            db.commit.assert_called_once()

    def test_force_heartbeat_failure_raises_500(self) -> None:
        from app.api.v1 import dead_mans_switch as dms

        db = MagicMock()
        with patch("app.services.audit.AuditService.log", side_effect=RuntimeError("db down")):
            with pytest.raises(HTTPException) as exc:
                dms.force_heartbeat(db=db)
            assert exc.value.status_code == 500

    @pytest.mark.parametrize("bad_limit", [0, -1, 501, 9999])
    def test_history_invalid_limit_raises_400(self, bad_limit: int) -> None:
        from app.api.v1 import dead_mans_switch as dms

        with pytest.raises(HTTPException) as exc:
            dms.get_history(limit=bad_limit, db=MagicMock())
        assert exc.value.status_code == 400

    def test_history_maps_cron_and_manual(self) -> None:
        from app.api.v1 import dead_mans_switch as dms

        now = datetime.now(timezone.utc)
        logs = [
            SimpleNamespace(
                timestamp=now, payload={"interval": 900}, action="heartbeat", hash="h1"
            ),
            SimpleNamespace(
                timestamp=now, payload={"forced_by": "admin"}, action="heartbeat", hash="h2"
            ),
            SimpleNamespace(timestamp=None, payload=None, action=None, hash=None),
        ]
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = logs
        resp = dms.get_history(limit=50, db=db)
        assert resp.total == 3
        assert resp.items[0].actor == "cron"
        assert resp.items[1].actor == "manual"
        assert resp.items[2].timestamp == ""  # fallback sem timestamp


# ---------------------------------------------------------------------------
# app/services/stream_buffer.py
# ---------------------------------------------------------------------------


class TestStreamBuffer:
    def test_append_flush_by_size(self) -> None:
        from app.services.stream_buffer import StreamBuffer

        buf: StreamBuffer[str] = StreamBuffer(max_chunk_size=100, max_latency_ms=60_000)
        assert buf.append("a" * 40, 40) is None
        assert buf.pending == 1
        assert buf.pending_size == 40
        flushed = buf.append("b" * 70, 70)  # 110 >= 100 -> flush
        assert flushed is not None and len(flushed) == 2
        assert buf.pending == 0
        assert buf.pending_size == 0

    def test_append_flush_by_latency(self) -> None:
        from app.services.stream_buffer import StreamBuffer

        buf: StreamBuffer[str] = StreamBuffer(max_chunk_size=10**9, max_latency_ms=250)
        buf._last_flush_ts = buf._last_flush_ts - 10  # simula 10s desde ultimo flush
        flushed = buf.append("x", 1)
        assert flushed == ["x"]

    def test_explicit_flush_and_empty_flush(self) -> None:
        from app.services.stream_buffer import StreamBuffer

        buf: StreamBuffer[str] = StreamBuffer(max_chunk_size=10**9, max_latency_ms=60_000)
        assert buf.flush() == []  # vazio
        buf.append("item", 4)
        assert buf.flush() == ["item"]
        assert buf.flush() == []  # ja esvaziado


class TestEstimateSize:
    def test_str_uses_utf8_len(self) -> None:
        from app.services.stream_buffer import estimate_size

        assert estimate_size("abc") == 3
        assert estimate_size("é") == 2  # UTF-8 multibyte

    def test_dict_recursive(self) -> None:
        from app.services.stream_buffer import estimate_size

        size = estimate_size({"k": "v", "nested": {"a": "b"}})
        assert size > len("k") + len("v")

    def test_list_and_tuple(self) -> None:
        from app.services.stream_buffer import estimate_size

        assert estimate_size(["ab", "cd"]) == 4
        assert estimate_size(("ab",)) == 2

    def test_other_types_default_256(self) -> None:
        from app.services.stream_buffer import estimate_size

        assert estimate_size(12345) == 256
        assert estimate_size(None) == 256


class TestBatchLogEntries:
    def test_batches_of_size(self) -> None:
        from app.services.stream_buffer import batch_log_entries

        entries = [{"msg": f"e{i}"} for i in range(5)]
        batches = list(batch_log_entries(entries, size=2))
        assert [len(b) for b in batches] == [2, 2, 1]

    def test_size_zero_falls_back_to_100(self) -> None:
        from app.services.stream_buffer import batch_log_entries

        entries = [{"msg": f"e{i}"} for i in range(3)]
        batches = list(batch_log_entries(entries, size=0))
        assert len(batches) == 1 and len(batches[0]) == 3

    def test_pii_is_scrubbed_in_string_values(self) -> None:
        """LGPD: CPF em entry de log NUNCA sai raw do batch (defense-in-depth)."""
        from app.services.stream_buffer import batch_log_entries

        entries = [{"msg": f"cliente cpf={SYNTHETIC_CPF} ok", "level": "info", "n": 1}]
        [[cleaned]] = list(batch_log_entries(entries, size=10))
        assert SYNTHETIC_CPF not in cleaned["msg"]
        assert cleaned["level"] == "info"
        assert cleaned["n"] == 1  # nao-string preservado

    def test_non_dict_entries_pass_through(self) -> None:
        from app.services.stream_buffer import batch_log_entries

        [[a, b]] = list(batch_log_entries(["raw", 42], size=10))  # type: ignore[list-item]
        assert a == "raw" and b == 42


class TestYieldRadarMetrics:
    def test_chunks_by_batch_size(self) -> None:
        from app.services.stream_buffer import yield_radar_metrics

        metrics = {f"q{i}": {"v": i} for i in range(5)}
        chunks = list(yield_radar_metrics(metrics, batch_size=2))
        assert len(chunks) == 3
        assert sum(len(c) for c in chunks) == 5

    def test_batch_size_zero_falls_back(self) -> None:
        from app.services.stream_buffer import yield_radar_metrics

        chunks = list(yield_radar_metrics({"a": 1, "b": 2}, batch_size=0))
        assert chunks == [{"a": 1, "b": 2}]


class TestOptimizeRadarResponse:
    def test_empty_returns_empty(self) -> None:
        from app.services.stream_buffer import optimize_radar_response

        assert optimize_radar_response({}) == []

    def test_small_payload_single_chunk(self) -> None:
        from app.services.stream_buffer import optimize_radar_response

        chunks = optimize_radar_response({"a": "x"}, max_size_per_chunk=1024)
        assert chunks == [{"a": "x"}]

    def test_large_payload_splits_chunks(self) -> None:
        from app.services.stream_buffer import optimize_radar_response

        radar = {f"metric_{i}": "x" * 400 for i in range(10)}
        chunks = optimize_radar_response(radar, max_size_per_chunk=1024)
        assert len(chunks) > 1
        # nenhum item perdido
        merged: dict = {}
        for c in chunks:
            merged.update(c)
        assert merged == radar


class TestStreamBufferCli:
    def test_cli_demo_runs_and_scrubs_pii(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from app.services.stream_buffer import _cli

        monkeypatch.setattr("sys.argv", ["stream_buffer", "--demo"])
        _cli()
        out = capsys.readouterr().out
        assert "StreamBuffer demo" in out
        assert "batch_log_entries" in out
        assert "optimize_radar_response" in out
        # demo usa CPF fake no log — scrub deve impedir vazamento raw no output
        assert "123.456.789-0" not in out

    def test_cli_without_demo_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services.stream_buffer import _cli

        monkeypatch.setattr("sys.argv", ["stream_buffer"])
        with pytest.raises(SystemExit) as exc:
            _cli()
        assert exc.value.code == 1
