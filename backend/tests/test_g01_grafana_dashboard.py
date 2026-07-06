"""Tests for the G01 operational overview Grafana dashboard.

These tests validate the JSON file shipped in infra/grafana/dashboards/
WITHOUT requiring a running Grafana instance. They enforce:

- 12 panels exactly, in IDs 1..12, in order
- Schema version + required fields
- All PromQL queries use REAL metric names exposed by A02/A13/A15/A14
- No PII labels leak into queries (LGPD art. 11)
- All targets point to the provisioned Prometheus datasource
- Panel types are from the allow-list (stat / timeseries)
- Descriptions are non-empty (operational hand-off / runbook hint)

Source of truth for metric names: backend/app/services/metrics.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

DASHBOARD_PATH = (
    Path(__file__).resolve().parents[2]
    / "infra"
    / "grafana"
    / "dashboards"
    / "cartorio-overview-12panels.json"
)

# Real metric names exposed by backend/app/services/metrics.py.
# See the docstring of that module for the canonical list.
REAL_METRICS = frozenset(
    {
        # HTTP requests counter (A02)
        "cartorio_http_requests_total",
        # HTTP request duration summary (A02) — count + sum only, no buckets
        "cartorio_http_request_duration_seconds_count",
        "cartorio_http_request_duration_seconds_sum",
        # Domain gauges (DB snapshot)
        "cartorio_clientes_total",
        "cartorio_protocolos_total",
        "cartorio_audit_chain_length",
        # A13 dead-man-switch
        "audit_dead_mans_status",
        # A14 backup
        "backup_last_success_timestamp_seconds",
        # A15 DB pool
        "cartorio_db_pool_checked_out",
        "cartorio_db_pool_size",
        "cartorio_db_pool_overflow",
        "cartorio_db_pool_max_overflow",
        "cartorio_db_pool_total_capacity",
        "cartorio_db_pool_utilization_pct",
        # A02 LGPD counters / summaries
        "pii_blocked_total",
        "scrub_latency_ms_count",
        "scrub_latency_ms_sum",
        "dlq_depth",
        "cartorio_pii_blocks_total",
        # B10 N8N (not used in this dashboard)
        "n8n_wf_executions_total",
        "n8n_wf_duration_seconds_count",
        "n8n_wf_duration_seconds_sum",
        "n8n_wf_error_rate",
        # E07 agents
        "agent_tokens_in_total",
        "agent_tokens_out_total",
        "agent_think_tokens_total",
        "agent_latency_seconds",
        "agent_requests_total",
        # Process
        "cartorio_uptime_seconds",
    }
)

# Forbidden substrings (LGPD art. 11 — PII). Any of these in a query is a fail.
PII_FORBIDDEN = (
    "cpf",
    "email",
    "phone",
    "telefone",
    "rg ",
    "cns",
    "cnh",
    "session_id",
    "request_id",
    "user_email",
    "cpf_value",
)

ALLOWED_PANEL_TYPES = frozenset({"stat", "timeseries"})


@pytest.fixture(scope="module")
def dashboard() -> dict:
    assert DASHBOARD_PATH.exists(), (
        f"dashboard JSON not found at {DASHBOARD_PATH} — "
        f"run infra/grafana/dashboards/_generate/build_overview_dashboard.py first"
    )
    return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))


def test_dashboard_schema_version_is_28(dashboard: dict) -> None:
    """Match existing dashboards (cartorio-api-overview.json)."""
    assert dashboard["schemaVersion"] == 28


def test_dashboard_has_required_metadata(dashboard: dict) -> None:
    assert dashboard["title"] == "Cartório — Operational Overview (12 panels)"
    assert dashboard["uid"] == "cartorio-overview-g01"
    assert dashboard["refresh"] == "30s"
    assert dashboard["timezone"] == "America/Sao_Paulo"
    assert "cartorio" in dashboard["tags"]
    assert "squad-g" in dashboard["tags"]
    assert "production" in dashboard["tags"]


def test_dashboard_has_exactly_12_panels(dashboard: dict) -> None:
    panels = dashboard["panels"]
    assert len(panels) == 12, f"expected 12 panels, got {len(panels)}"


def test_panel_ids_are_1_through_12_in_order(dashboard: dict) -> None:
    ids = [p["id"] for p in dashboard["panels"]]
    assert ids == list(range(1, 13)), f"panel ids must be 1..12, got {ids}"


def test_all_panels_have_targets(dashboard: dict) -> None:
    for panel in dashboard["panels"]:
        assert panel.get("targets"), f"panel {panel['id']} has no targets"
        for target in panel["targets"]:
            assert target.get("expressions"), f"panel {panel['id']} target missing expressions"
            expr = target["expressions"][0]
            assert isinstance(expr, str) and expr.strip(), (
                f"panel {panel['id']} has empty expression"
            )


def test_all_panel_types_allowed(dashboard: dict) -> None:
    for panel in dashboard["panels"]:
        assert panel["type"] in ALLOWED_PANEL_TYPES, (
            f"panel {panel['id']} uses disallowed type {panel['type']!r}"
        )


def test_all_panels_have_descriptions(dashboard: dict) -> None:
    """Operational hand-off: every panel must document what it shows + gaps."""
    for panel in dashboard["panels"]:
        desc = panel.get("description", "")
        assert len(desc.strip()) >= 20, (
            f"panel {panel['id']} description too short or missing: {desc!r}"
        )


def test_all_panels_use_provisioned_prometheus_datasource(dashboard: dict) -> None:
    """Datasource must be the provisioned one (uid=prometheus) — see
    infra/monitoring/grafana-datasources.yml."""
    for panel in dashboard["panels"]:
        ds = panel["datasource"]
        assert ds.get("uid") == "prometheus", (
            f"panel {panel['id']} datasource uid must be 'prometheus', got {ds}"
        )
        assert ds.get("type") == "prometheus", (
            f"panel {panel['id']} datasource type must be 'prometheus', got {ds}"
        )


def test_no_pii_in_any_query(dashboard: dict) -> None:
    """LGPD art. 11: no PII labels leak to Prometheus queries."""
    for panel in dashboard["panels"]:
        for target in panel["targets"]:
            expr = target["expressions"][0].lower()
            for forbidden in PII_FORBIDDEN:
                assert forbidden not in expr, (
                    f"panel {panel['id']} query contains forbidden PII label {forbidden!r}: {expr}"
                )


# Match plausible Prometheus metric names (snake_case with prefix).
_METRIC_TOKEN = re.compile(r"\b([a-z][a-z0-9_]+)\b")


def _extract_metric_names(query: str) -> set[str]:
    """Extract plausible metric names from a PromQL query.

    Filters out known PromQL keywords and dashboard label names.
    """
    candidates: set[str] = set()
    ignored_tokens = {
        "by", "sum", "rate", "histogram_quantile",
        "endpoint", "status", "tipo_scrub",
    }
    for match in _METRIC_TOKEN.finditer(query):
        token = match.group(1)
        if token.startswith("__") or token in ignored_tokens:
            continue
        candidates.add(token)
    return candidates


def test_all_referenced_metrics_are_real(dashboard: dict) -> None:
    """Every metric referenced in a panel must exist in the metrics service."""
    all_metrics_used: set[str] = set()
    for panel in dashboard["panels"]:
        for target in panel["targets"]:
            all_metrics_used |= _extract_metric_names(target["expressions"][0])

    unknown = all_metrics_used - REAL_METRICS
    assert not unknown, (
        f"queries reference unknown metric names: {sorted(unknown)}. "
        f"Add them to backend/app/services/metrics.py FIRST, then to REAL_METRICS."
    )


def test_panel_1_throughput_uses_correct_metric(dashboard: dict) -> None:
    panel = next(p for p in dashboard["panels"] if p["id"] == 1)
    expr = panel["targets"][0]["expressions"][0]
    assert "cartorio_http_requests_total" in expr
    assert "rate(" in expr
    assert "[1m]" in expr
    assert "* 60" in expr  # per-minute normalisation


def test_panel_2_error_rate_pct_uses_correct_metrics(dashboard: dict) -> None:
    panel = next(p for p in dashboard["panels"] if p["id"] == 2)
    expr = panel["targets"][0]["expressions"][0]
    assert "cartorio_http_requests_total" in expr
    assert 'status=~"4..|5.."' in expr
    assert "/" in expr  # ratio


def test_panel_9_uses_audit_dead_mans_status(dashboard: dict) -> None:
    """A13 metric must be present in panel 9."""
    panel = next(p for p in dashboard["panels"] if p["id"] == 9)
    expr = panel["targets"][0]["expressions"][0]
    assert expr.strip() == "audit_dead_mans_status"


def test_panel_3_uses_db_pool_metric(dashboard: dict) -> None:
    """A15 metric must be present in panel 3."""
    panel = next(p for p in dashboard["panels"] if p["id"] == 3)
    expr = panel["targets"][0]["expressions"][0]
    assert expr.strip() == "cartorio_db_pool_utilization_pct"


def test_no_grid_overlap(dashboard: dict) -> None:
    """Sanity: panels should not occupy the same grid cell."""
    seen: set[tuple[int, int]] = set()
    for panel in dashboard["panels"]:
        gp = panel["gridPos"]
        cell = (gp["x"], gp["y"])
        assert cell not in seen, (
            f"panel {panel['id']} shares grid start ({cell}) with another panel"
        )
        seen.add(cell)
