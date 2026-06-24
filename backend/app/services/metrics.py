"""Service de metrics Prometheus (open source, sem vendor).

Endpoint: GET /api/v1/metrics/prometheus (formato text/plain, version 0.0.4).

Por que Prometheus e nao vendor:
- Open source (Apache 2.0)
- Formato text simples, sem SDK
- Funciona com Grafana/Mimir/Thanos/etc (ecosistema padrao)
- Sem lock-in (vendor migracao = 1 dia)
- Sem dados enviados pra terceiros

Metricas expostas (A1+A2):
- cartorio_http_requests_total{endpoint, method, status} - counter
- cartorio_http_request_duration_seconds{endpoint, method} - histogram
- cartorio_protocolos_total{status} - gauge (snapshot)
- cartorio_clientes_total - gauge
- cartorio_audit_chain_length - gauge
- cartorio_pii_blocks_total{type} - counter (legacy)
- pii_blocked_total{tipo_scrub, channel} - counter (A2 LGPD)
- scrub_latency_ms{tipo_scrub, result} - summary (A2 LGPD)
- dlq_depth{queue} - gauge (A2 LGPD)
- cartorio_uptime_seconds - gauge
"""
from __future__ import annotations

import time
from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo


class MetricsStore:
    """Singleton in-memory para metrics (reset a cada restart do processo).

    Cardinalidade de labels eh controlada via enums:
    - tipo_scrub: cpf | rg | telefone | email | cns | cnh | none
    - channel:    whatsapp | telegram | web | api
    - result:     blocked | allowed
    - queue:      evolution | chatwoot | telegram | outbox
    SEM session_id / cpf_value / user_email / request_id (explodem cardinalidade
    OU vazam PII).
    """

    def __init__(self) -> None:
        # counters: {metric_name: {labels_key: value}}
        self.counters: dict[str, dict[str, int]] = {}
        # histograms: {metric_name: {labels_key: [observations]}}
        self.histograms: dict[str, dict[str, list[float]]] = {}
        # gauges: {metric_name: scalar OR {labels_key: value}}
        self.gauges: dict[str, Any] = {}
        # registry para idempotencia do factory (chave -> handle)
        self._metric_registry: dict[str, _MetricHandle] = {}
        self._started_at: float = time.time()

    def inc_counter(
        self, name: str, labels: dict[str, str] | None = None, value: int = 1
    ) -> None:
        key = self._labels_key(labels)
        self.counters.setdefault(name, {}).setdefault(key, 0)
        self.counters[name][key] += value

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        key = self._labels_key(labels)
        self.histograms.setdefault(name, {}).setdefault(key, [])
        self.histograms[name][key].append(value)

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Store gauge. With labels -> dict[labels_key, value]. Without -> scalar."""
        if labels:
            key = self._labels_key(labels)
            existing = self.gauges.get(name)
            if not isinstance(existing, dict):
                old = existing
                self.gauges[name] = {}
                if old is not None:
                    self.gauges[name][""] = old
            self.gauges[name][key] = value
        else:
            self.gauges[name] = value

    def _make_metric_or_skip_test(self, name: str, metric_type: str) -> "_MetricHandle":
        """Factory idempotente (A2 best practice).

        - Mesmo nome+type -> retorna mesma referencia (idempotente).
        - Nome diferente -> retorna nova referencia (nao colapsa).
        """
        if metric_type not in ("counter", "histogram", "gauge"):
            raise ValueError(f"metric_type invalido: {metric_type!r}")
        registry_key = f"{metric_type}:{name}"
        existing = self._metric_registry.get(registry_key)
        if existing is None:
            handle = _MetricHandle(name=name, metric_type=metric_type, store=self)
            self._metric_registry[registry_key] = handle
            return handle
        return existing

    def track_scrub_latency(
        self, tipo_scrub: str, result: str, duration_ms: float
    ) -> None:
        """Helper A2: histogram scrub_latency_ms{tipo_scrub,result}."""
        self._make_metric_or_skip_test("scrub_latency_ms", "histogram")
        self.observe_histogram(
            "scrub_latency_ms",
            duration_ms,
            labels={"tipo_scrub": tipo_scrub, "result": result},
        )

    def inc_pii_blocked(self, tipo_scrub: str, channel: str) -> None:
        """Helper A2: counter pii_blocked_total{tipo_scrub,channel}."""
        self._make_metric_or_skip_test("pii_blocked_total", "counter")
        self.inc_counter(
            "pii_blocked_total",
            labels={"tipo_scrub": tipo_scrub, "channel": channel},
        )

    def set_dlq_depth(self, queue: str, depth: int) -> None:
        """Helper A2: gauge dlq_depth{queue}."""
        self._make_metric_or_skip_test("dlq_depth", "gauge")
        self.set_gauge("dlq_depth", float(depth), labels={"queue": queue})

    def _labels_key(self, labels: dict[str, str] | None) -> str:
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _parse_labels_key(self, key: str) -> dict[str, str]:
        if not key:
            return {}
        return dict(item.split("=", 1) for item in key.split("|") if "=" in item)

    def _labels_render(self, labels: dict[str, str] | None) -> str:
        """Render labels no formato Prometheus text (key="value",...)."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def render_prometheus(self) -> str:
        """Renderiza tudo no formato text/plain do Prometheus (version 0.0.4)."""
        lines: list[str] = []

        # Counters
        counters: dict[str, dict[str, int]] = cast(
            "dict[str, dict[str, int]]", self.counters
        )
        for name, buckets in counters.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} counter")
            for key, value in buckets.items():
                label_dict = self._parse_labels_key(key)
                label_str = (
                    "{" + self._labels_render(label_dict) + "}" if label_dict else ""
                )
                lines.append(f"{name}{label_str} {int(value)}")

        # Histograms (formato simplificado: count + sum, suficiente p/ cartorio)
        histograms: dict[str, dict[str, list[float]]] = cast(
            "dict[str, dict[str, list[float]]]", self.histograms
        )
        for name, buckets in histograms.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} summary")
            for key, values in buckets.items():  # type: ignore[assignment]
                label_dict = self._parse_labels_key(key)
                label_str = (
                    "{" + self._labels_render(label_dict) + "}" if label_dict else ""
                )
                lines.append(f"{name}_count{label_str} {len(values)}")  # type: ignore[arg-type]
                lines.append(
                    f"{name}_sum{label_str} {sum(values):.6f}"  # type: ignore[call-overload,arg-type]
                )

        # Gauges (suporta escalar E dict-com-labels)
        for name, val_or_map in self.gauges.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} gauge")
            if isinstance(val_or_map, dict):
                for key, value in val_or_map.items():  # type: ignore[union-attr]
                    label_dict = self._parse_labels_key(key)
                    label_str = (
                        "{" + self._labels_render(label_dict) + "}"
                        if label_dict
                        else ""
                    )
                    lines.append(f"{name}{label_str} {float(value):.6f}")
            else:
                lines.append(f"{name} {float(val_or_map):.6f}")  # type: ignore[arg-type]

        # Uptime sempre
        lines.append("# TYPE cartorio_uptime_seconds gauge")
        lines.append(f"cartorio_uptime_seconds {time.time() - self._started_at:.6f}")
        return "\n".join(lines) + "\n"


# Singleton global
store = MetricsStore()


class _MetricHandle:
    """Handle leve retornado por _make_metric_or_skip_test.

    - Mesmo nome+type -> mesma instancia (idempotente via _metric_registry).
    - Nome diferente -> instancia nova (handles distintos).
    Usado apenas como token de identidade; metodos de fato ficam no store pai.
    """

    __slots__ = ("name", "metric_type", "store", "_id")

    _counter: int = 0

    def __init__(self, name: str, metric_type: str, store: MetricsStore) -> None:
        _MetricHandle._counter += 1
        self._id = _MetricHandle._counter
        self.name = name
        self.metric_type = metric_type
        self.store = store

    def __repr__(self) -> str:
        return f"_MetricHandle(name={self.name!r}, type={self.metric_type!r}, id={self._id})"


def collect_db_metrics(db: Session) -> dict[str, Any]:
    """Coleta metrics do DB (gauge snapshot). Chamado pelo endpoint /metrics/prometheus."""
    metrics: dict[str, Any] = {}
    metrics["clientes_total"] = db.query(func.count(Cliente.id)).scalar() or 0
    rows = (
        db.query(Protocolo.status, func.count(Protocolo.id))
        .group_by(Protocolo.status)
        .all()
    )
    for status, count in rows:
        metrics[f'protocolos_total{{status="{status}"}}'] = count
    metrics["audit_chain_length"] = db.query(func.count(AuditLog.id)).scalar() or 0
    return metrics


def render_full_prometheus(db: Session | None = None) -> str:
    """Renderiza todos os metrics incluindo snapshot do DB."""
    if db is not None:
        for name, value in collect_db_metrics(db).items():
            store.set_gauge(name, value)
    return store.render_prometheus()


def render_metrics_json(db: Session | None = None) -> dict[str, Any]:
    """Renderiza metrics como dict JSON (consumivel por N8N workflows).

    Shape canonico (Sprint 4 STREAM 1 - 2026-06-24):
    - clientes_total: int
    - protocolos_total: dict[status, int] - separa prefixo 'protocolos_total{status="..."}'
      para dict puro
    - audit_chain_length: int
    - uptime_seconds: float
    - counters: dict[str, dict[labels_key, int]] - contadores in-process
    - gauges: dict[str, dict | scalar] - gauges in-process

    LGPD: NAO expoe PII. Apenas contadores agregados.
    """
    # Snapshot do DB (gauge values)
    db_snapshot: dict[str, Any] = {}
    if db is not None:
        db_snapshot = collect_db_metrics(db)

    # Processa db_snapshot -> campos canonicos
    clientes_total = int(db_snapshot.get("clientes_total", 0))
    audit_chain_length = int(db_snapshot.get("audit_chain_length", 0))

    # protocolos_total: prefix 'protocolos_total{status="..."}' -> dict puro
    protocolos_total: dict[str, int] = {}
    for key, value in db_snapshot.items():
        if key.startswith('protocolos_total{status="') and key.endswith('"}'):
            # Extrai status entre 'protocolos_total{status="' e '"}'
            status = key[len('protocolos_total{status="') : -len('"}')]
            protocolos_total[status] = int(value)

    # In-process metrics (counters e gauges)
    # Counters: {name: {labels_key: int}} -> {name: {labels_key: int}}
    counters: dict[str, dict[str, int]] = {}
    for name, buckets in store.counters.items():
        counters[name] = dict(buckets)

    # Gauges: suporta scalar E dict-com-labels -> normaliza pra JSON
    gauges: dict[str, Any] = {}
    for name, val_or_map in store.gauges.items():
        if isinstance(val_or_map, dict):
            gauges[name] = dict(val_or_map)
        else:
            gauges[name] = float(val_or_map)

    # Uptime sempre presente (reusa logica do render_prometheus)
    uptime_seconds = float(time.time() - store._started_at)

    return {
        "clientes_total": clientes_total,
        "protocolos_total": protocolos_total,
        "audit_chain_length": audit_chain_length,
        "uptime_seconds": uptime_seconds,
        "counters": counters,
        "gauges": gauges,
    }