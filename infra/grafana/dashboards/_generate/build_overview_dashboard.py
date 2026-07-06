"""Build the Cartório operational overview Grafana dashboard (G01).

WHY THIS EXISTS
---------------
The briefing for G01 (Squad G — Hardening Prod SRE) asked for 12 panels
covering API latency (p50/p95/p99), error rate, throughput, CPU/RAM/disk,
Redis queue depth, audit dead-man-switch, and uptime.

REALITY (Lesson 110 / briefing-verification protocol)
----------------------------------------------------
1. The metric names hypothesised in the briefing (latency_api_ms_bucket,
   http_requests_total, container_cpu_usage_seconds_total, redis_db_keys,
   etc.) DO NOT MATCH the names exposed by the actual A02/A15/A13 metrics
   services. We use the REAL metric names from backend/app/services/metrics.py
   instead of inventing fictitious ones.

2. The API exposes its metrics as PROMETHEUS SUMMARIES (count + sum only),
   not as histograms with _bucket suffix. histogram_quantile() therefore
   does not work for latency p50/p95/p99 — we surface AVG latency instead
   and document the percentile gap. Closing that gap is an A26 follow-up
   (proper histogram with buckets), out of scope for G01.

3. CPU / RAM / disk / Redis queue depth are NOT exposed today because
   node_exporter + cadvisor + redis_exporter are not deployed. Those
   panels are SKIPPED in this dashboard; instead we surface operational
   metrics that ARE available (A15 pool, audit chain, LGPD PII, uptime).

4. Squad C already deployed the monitoring stack (commit dd308f5 — Grafana,
   Prometheus, Loki, Promtail, datasources, provisioning, 2 existing
   dashboards). We re-use the existing datasource (uid=prometheus) and
   folder (Cartório) — see infra/monitoring/grafana-dashboards.yml.

RUN
---
    python infra/grafana/dashboards/_generate/build_overview_dashboard.py

Writes:
    infra/grafana/dashboards/cartorio-overview-12panels.json

Panel map (12 panels total, schema v28, Grafana >= 9.0):
  1.  Total Requests/min              (stat, last 5m)
  2.  Error Rate % (4xx+5xx)          (stat with thresholds)
  3.  DB Pool Utilization % (A15)     (stat with thresholds)
  4.  Audit Chain Length              (stat, deltas over time)
  5.  Throughput by endpoint          (timeseries, req/s)
  6.  Error rate split 4xx / 5xx      (timeseries by status)
  7.  Avg Latency by endpoint         (timeseries, seconds)
  8.  PII Blocks by tipo_scrub        (timeseries, blocks/s)
  9.  Audit Dead-man-switch status    (stat with thresholds; 0=healthy)
  10. LGPD Scrub latency (avg)        (timeseries, ms)
  11. Clientes + Protocolos totals    (timeseries, gauge snapshots)
  12. System Uptime                   (stat, formatted duration)

LGPD: no PII labels are queried (no cpf, no email, no phone, no session_id).
All queries use aggregate counters / gauges.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants — datasource + scope
# ---------------------------------------------------------------------------

DATASOURCE_UID = "prometheus"  # provisioned by infra/monitoring/grafana-datasources.yml
SCHEMA_VERSION = 28  # Grafana 9.0+ — matches existing dashboards
DASHBOARD_TITLE = "Cartório — Operational Overview (12 panels)"
DASHBOARD_TAGS = ["cartorio", "production", "squad-g", "operational-health", "g01"]
DASHBOARD_TIMEZONE = "America/Sao_Paulo"
DASHBOARD_TIME_FROM = "now-6h"
DASHBOARD_TIME_TO = "now"
DASHBOARD_REFRESH = "30s"
DASHBOARD_UID = "cartorio-overview-g01"  # stable for deep links / annotations

# Common Prometheus query parameters
RATE_5M = "rate(...[5m])"
RATE_1M = "rate(...[1m])"

# Output paths
HERE = Path(__file__).resolve().parent
OUTPUT_JSON = HERE.parent / "cartorio-overview-12panels.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expr(query: str) -> dict[str, Any]:
    """Wrap a PromQL string in the {expressions: [...]} envelope."""
    return {"expressions": [query], "refId": "A"}


def _grid_pos(x: int, y: int, w: int, h: int) -> dict[str, int]:
    return {"x": x, "y": y, "w": w, "h": h}


def _datasource() -> dict[str, str]:
    return {"type": "prometheus", "uid": DATASOURCE_UID}


def _panel(
    *,
    panel_id: int,
    title: str,
    panel_type: str,
    grid: dict[str, int],
    targets: list[dict[str, Any]],
    field_config: dict[str, Any],
    options: dict[str, Any],
    description: str = "",
) -> dict[str, Any]:
    """Build a standard Grafana panel object."""
    return {
        "id": panel_id,
        "type": panel_type,
        "title": title,
        "description": description,
        "datasource": _datasource(),
        "gridPos": grid,
        "targets": targets,
        "fieldConfig": field_config,
        "options": options,
    }


def _thresholds(*steps: tuple[int | None, str]) -> dict[str, Any]:
    """Build thresholds.steps from (value, color) tuples."""
    return {
        "mode": "absolute",
        "steps": [{"color": color, "value": value} for value, color in steps],
    }


# ---------------------------------------------------------------------------
# Panels — 12 total, in display order
# ---------------------------------------------------------------------------


def panel_01_total_requests_per_min() -> dict[str, Any]:
    """Total Requests/min — single stat (last 1m rate * 60)."""
    return _panel(
        panel_id=1,
        title="Requests/min (total)",
        panel_type="stat",
        grid=_grid_pos(0, 0, 6, 6),
        targets=[_expr("sum(rate(cartorio_http_requests_total[1m])) * 60")],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": _thresholds(
                    (None, "green"),
                    (100, "yellow"),
                    (1000, "red"),
                ),
                "unit": "short",
                "decimals": 0,
            },
            "overrides": [],
        },
        options={
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        description=(
            "Total HTTP requests per minute (sum across all endpoints). "
            "Threshold >1000/min sustained = investigate traffic spike."
        ),
    )


def panel_02_error_rate_pct() -> dict[str, Any]:
    """Error Rate % — single stat, 4xx+5xx / total."""
    err_expr = (
        'sum(rate(cartorio_http_requests_total{status=~"4..|5.."}[5m]))'
        "/"
        "sum(rate(cartorio_http_requests_total[5m]))"
    )
    return _panel(
        panel_id=2,
        title="Error Rate % (4xx+5xx)",
        panel_type="stat",
        grid=_grid_pos(6, 0, 6, 6),
        targets=[_expr(err_expr)],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": _thresholds(
                    (None, "green"),
                    (0.01, "yellow"),
                    (0.05, "red"),
                ),
                "unit": "percentunit",
                "decimals": 2,
            },
            "overrides": [],
        },
        options={
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        description=(
            "Fraction of HTTP responses with status 4xx or 5xx over the last 5 minutes. "
            "SLO: <1% sustained, page on >5%."
        ),
    )


def panel_03_db_pool_utilization() -> dict[str, Any]:
    """DB Pool Utilization % — gauge from A15."""
    return _panel(
        panel_id=3,
        title="DB Pool Utilization (A15)",
        panel_type="stat",
        grid=_grid_pos(12, 0, 6, 6),
        targets=[_expr("cartorio_db_pool_utilization_pct")],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": _thresholds(
                    (None, "green"),
                    (70, "yellow"),
                    (85, "red"),
                ),
                "unit": "percent",
                "decimals": 1,
            },
            "overrides": [],
        },
        options={
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        description=(
            "SQLAlchemy pool utilization (A15). P1 alert fires at >85% sustained 5m "
            "(see infra/prometheus/alerts.yml — CartorioDBPoolExhausted)."
        ),
    )


def panel_04_audit_chain_length() -> dict[str, Any]:
    """Audit Chain Length — stat with sparkline."""
    return _panel(
        panel_id=4,
        title="Audit Chain Length",
        panel_type="stat",
        grid=_grid_pos(18, 0, 6, 6),
        targets=[_expr("cartorio_audit_chain_length")],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": _thresholds((None, "blue")),
                "unit": "short",
                "decimals": 0,
            },
            "overrides": [],
        },
        options={
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        description=(
            "Total audit_log rows (monotonic counter via SQL snapshot). "
            "Should only increase. Drops indicate data tampering or DB corruption."
        ),
    )


def panel_05_throughput_by_endpoint() -> dict[str, Any]:
    """Throughput (req/s) by endpoint."""
    return _panel(
        panel_id=5,
        title="Throughput by endpoint (req/s)",
        panel_type="timeseries",
        grid=_grid_pos(0, 6, 12, 8),
        targets=[_expr("sum by (endpoint) (rate(cartorio_http_requests_total[5m]))")],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(),
                "unit": "reqps",
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description="HTTP requests/sec, broken down by endpoint label (A02).",
    )


def panel_06_error_rate_split() -> dict[str, Any]:
    """Error rate timeseries — split 4xx and 5xx."""
    return _panel(
        panel_id=6,
        title="Error rate by status class (4xx vs 5xx)",
        panel_type="timeseries",
        grid=_grid_pos(12, 6, 12, 8),
        targets=[
            _expr(
                'sum by (endpoint) (rate(cartorio_http_requests_total{status=~"4.."}[5m]))'
            ),
            _expr(
                'sum by (endpoint) (rate(cartorio_http_requests_total{status=~"5.."}[5m]))'
            ),
        ],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(),
                "unit": "reqps",
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description=(
            "4xx and 5xx rates per endpoint. Sustained 5xx > 0.01 req/s triggers "
            "P1 alert via Prometheus rule (see infra/prometheus/alerts.yml)."
        ),
    )


def panel_07_avg_latency() -> dict[str, Any]:
    """Avg latency per endpoint — derived from summary _sum / _count.

    NOTE: cartorio_http_request_duration_seconds is a SUMMARY (count + sum),
    not a histogram with _bucket suffix. histogram_quantile() therefore does
    not work. We compute AVG latency per endpoint as a proxy. Closing this
    gap requires migrating to a proper histogram (A26 follow-up).
    """
    avg_expr = (
        "sum by (endpoint) (rate(cartorio_http_request_duration_seconds_sum[5m]))"
        " / "
        "sum by (endpoint) (rate(cartorio_http_request_duration_seconds_count[5m]))"
    )
    return _panel(
        panel_id=7,
        title="Avg Latency by endpoint (s)",
        panel_type="timeseries",
        grid=_grid_pos(0, 14, 12, 8),
        targets=[_expr(avg_expr)],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(
                    (None, "green"),
                    (0.2, "yellow"),
                    (1.0, "red"),
                ),
                "unit": "s",
                "decimals": 3,
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description=(
            "AVG latency per endpoint (summary _sum / _count). SLO target <200ms; "
            "p50/p95/p99 percentiles require migrating to a proper histogram "
            "(A26 backlog — not exposed today)."
        ),
    )


def panel_08_pii_blocks() -> dict[str, Any]:
    """PII blocks per tipo_scrub — A02 LGPD."""
    return _panel(
        panel_id=8,
        title="PII Blocks (A02 LGPD)",
        panel_type="timeseries",
        grid=_grid_pos(12, 14, 12, 8),
        targets=[_expr("sum by (tipo_scrub) (rate(pii_blocked_total[5m]))")],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(),
                "unit": "ops",
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description=(
            "PII scrub blocks per second, split by tipo_scrub (cpf | rg | telefone | "
            "email | cns | cnh | none). Sustained high volume = upstream leak — "
            "investigate the source channel."
        ),
    )


def panel_09_audit_dead_mans_status() -> dict[str, Any]:
    """Audit dead-man-switch status — A13 (0=healthy, 1=warning, 2=critical)."""
    return _panel(
        panel_id=9,
        title="Audit Dead-man-switch (A13)",
        panel_type="stat",
        grid=_grid_pos(0, 22, 6, 6),
        targets=[_expr("audit_dead_mans_status")],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "0": {"text": "Healthy", "color": "green", "index": 0},
                            "1": {"text": "Warning", "color": "yellow", "index": 1},
                            "2": {"text": "Critical", "color": "red", "index": 2},
                        },
                    }
                ],
                "thresholds": _thresholds(
                    (None, "green"),
                    (1, "yellow"),
                    (2, "red"),
                ),
                "unit": "none",
                "decimals": 0,
            },
            "overrides": [],
        },
        options={
            "colorMode": "background",
            "graphMode": "none",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "value_and_name",
        },
        description=(
            "A13 dead-man-switch status. 0=Healthy, 1=Warning, 2=Critical. "
            "P0 alert: audit_dead_mans_status > 0 for 5m (see alerts.yml — "
            "CartorioAuditChainBroken)."
        ),
    )


def panel_10_scrub_latency() -> dict[str, Any]:
    """LGPD scrub latency (avg ms) — A02."""
    avg_expr = (
        "sum by (tipo_scrub) (rate(scrub_latency_ms_sum[5m]))"
        " / "
        "sum by (tipo_scrub) (rate(scrub_latency_ms_count[5m]))"
    )
    return _panel(
        panel_id=10,
        title="Scrub Latency (A02 LGPD, ms)",
        panel_type="timeseries",
        grid=_grid_pos(6, 22, 12, 6),
        targets=[_expr(avg_expr)],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(
                    (None, "green"),
                    (5, "yellow"),
                    (20, "red"),
                ),
                "unit": "ms",
                "decimals": 2,
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description=(
            "Average scrub latency per tipo_scrub (ms). Target: <5ms per scrub. "
            "Hot path for LLM-bound requests — sustained >20ms is a regression."
        ),
    )


def panel_11_clientes_protocolos_totals() -> dict[str, Any]:
    """Clientes + Protocolos totals (gauge snapshots over time)."""
    return _panel(
        panel_id=11,
        title="Domain Totals (clientes + protocolos)",
        panel_type="timeseries",
        grid=_grid_pos(18, 22, 6, 6),
        targets=[
            _expr("cartorio_clientes_total"),
            _expr("sum by (status) (cartorio_protocolos_total)"),
        ],
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "stepAfter",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "spanNulls": True,
                    "showPoints": "never",
                },
                "mappings": [],
                "thresholds": _thresholds(),
                "unit": "short",
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        description=(
            "Gauge snapshots of clientes_total + protocolos_total{status=*}. "
            "Step interpolation reflects periodic SQL COUNT refresh."
        ),
    )


def panel_12_uptime() -> dict[str, Any]:
    """System uptime — formatted duration."""
    return _panel(
        panel_id=12,
        title="System Uptime",
        panel_type="stat",
        grid=_grid_pos(0, 28, 24, 4),
        targets=[_expr("cartorio_uptime_seconds")],
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": _thresholds((None, "blue")),
                "unit": "s",
                "decimals": 0,
            },
            "overrides": [],
        },
        options={
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        description=(
            "Process uptime in seconds (reset on each restart). Use Grafana unit "
            "formatting to render as D/H/M. Drops to 0 = process restart."
        ),
    )


# ---------------------------------------------------------------------------
# Assemble dashboard
# ---------------------------------------------------------------------------


def build_dashboard() -> dict[str, Any]:
    """Build the full dashboard dict."""
    panels = [
        panel_01_total_requests_per_min(),
        panel_02_error_rate_pct(),
        panel_03_db_pool_utilization(),
        panel_04_audit_chain_length(),
        panel_05_throughput_by_endpoint(),
        panel_06_error_rate_split(),
        panel_07_avg_latency(),
        panel_08_pii_blocks(),
        panel_09_audit_dead_mans_status(),
        panel_10_scrub_latency(),
        panel_11_clientes_protocolos_totals(),
        panel_12_uptime(),
    ]

    return {
        "__inputs": [
            {
                "name": "DS_PROMETHEUS",
                "label": "Prometheus",
                "description": "Prometheus data source (provisioned via grafana-datasources.yml)",
                "type": "datasource",
                "pluginId": "prometheus",
                "pluginName": "Prometheus",
            }
        ],
        "__requires": [
            {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "9.0.0"},
            {
                "type": "datasource",
                "id": "prometheus",
                "name": "Prometheus",
                "version": "1.0.0",
            },
            {"type": "panel", "id": "stat", "name": "Stat", "version": ""},
            {"type": "panel", "id": "timeseries", "name": "Time series", "version": ""},
        ],
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "description": (
            "Cartório 2notas — operational health overview (12 panels). "
            "Built by Squad G (G01). See .harness/reins/cartorio-dev/memory/"
            "G01-grafana.md for the panel-to-metric mapping and known gaps "
            "(CPU/RAM/disk pending node_exporter; Redis DBSIZE pending "
            "redis_exporter; histogram percentiles pending A26 migration)."
        ),
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": panels,
        "refresh": DASHBOARD_REFRESH,
        "schemaVersion": SCHEMA_VERSION,
        "tags": DASHBOARD_TAGS,
        "templating": {"list": []},
        "time": {"from": DASHBOARD_TIME_FROM, "to": DASHBOARD_TIME_TO},
        "timepicker": {},
        "timezone": DASHBOARD_TIMEZONE,
        "title": DASHBOARD_TITLE,
        "uid": DASHBOARD_UID,
        "version": 1,
        "weekStart": "",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    dashboard = build_dashboard()

    # Sanity assertions before writing
    assert len(dashboard["panels"]) == 12, (
        f"expected 12 panels, got {len(dashboard['panels'])}"
    )
    panel_ids = [p["id"] for p in dashboard["panels"]]
    assert panel_ids == list(range(1, 13)), f"panel ids must be 1..12, got {panel_ids}"

    # Write deterministically (sorted keys, 2-space indent)
    OUTPUT_JSON.write_text(
        json.dumps(dashboard, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"WROTE {OUTPUT_JSON.relative_to(HERE.parent.parent.parent)}")
    print(f"  panels: {len(dashboard['panels'])}")
    print(f"  uid:    {DASHBOARD_UID}")
    print(f"  tags:   {DASHBOARD_TAGS}")


if __name__ == "__main__":
    main()
