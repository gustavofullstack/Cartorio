"""J10 - Valida OpenTelemetry collector config YAML.

Verifica que infra/observability/otel-collector-config.yml:
- Tem receivers OTLP (gRPC + HTTP)
- Tem exporters (Jaeger + Prometheus + logging)
- Tem service pipelines (traces + metrics + logs)
- Tem memory_limiter processor (production-ready)
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[2]
OTEL_CONFIG = REPO_ROOT / "infra" / "observability" / "otel-collector-config.yml"


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_exists_and_valid_yaml() -> None:
    """Arquivo existe e parseia como YAML."""
    assert OTEL_CONFIG.exists(), f"OTel config nao encontrado: {OTEL_CONFIG}"
    content = OTEL_CONFIG.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict)
    assert "receivers" in parsed
    assert "exporters" in parsed
    assert "service" in parsed


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_has_otlp_receiver() -> None:
    """Receiver OTLP presente com gRPC + HTTP."""
    parsed = yaml.safe_load(OTEL_CONFIG.read_text(encoding="utf-8"))
    assert "otlp" in parsed["receivers"]
    otlp = parsed["receivers"]["otlp"]
    assert "protocols" in otlp
    assert "grpc" in otlp["protocols"]
    assert "http" in otlp["protocols"]


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_has_required_exporters() -> None:
    """Exporters: jaeger (traces), prometheus (metrics), logging."""
    parsed = yaml.safe_load(OTEL_CONFIG.read_text(encoding="utf-8"))
    exporters = parsed["exporters"]
    assert any("jaeger" in k for k in exporters), f"Sem exporter Jaeger: {list(exporters)}"
    assert "prometheus" in exporters
    assert "logging" in exporters


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_service_pipelines() -> None:
    """Service tem pipelines para traces, metrics, logs."""
    parsed = yaml.safe_load(OTEL_CONFIG.read_text(encoding="utf-8"))
    pipelines = parsed["service"]["pipelines"]
    assert "traces" in pipelines
    assert "metrics" in pipelines
    assert "logs" in pipelines


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_has_memory_limiter() -> None:
    """Memory limiter obrigatorio para production."""
    parsed = yaml.safe_load(OTEL_CONFIG.read_text(encoding="utf-8"))
    assert "memory_limiter" in parsed["processors"]


@pytest.mark.skipif(yaml is None, reason="pyyaml nao instalado")
def test_otel_config_has_batch_processor() -> None:
    """Batch processor para reduzir overhead."""
    parsed = yaml.safe_load(OTEL_CONFIG.read_text(encoding="utf-8"))
    assert "batch" in parsed["processors"]
