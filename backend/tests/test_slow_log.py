"""Testes do SlowLogMiddleware.

Cobertura:
- Request < threshold NAO emite log
- Request >= threshold emite log WARNING/INFO estruturado
- Skip paths (/health, /metrics, /docs) NAO emitem log mesmo se lentas
- Log contem method, path, status_code, duration_ms, request_id, client_ip
- Threshold customizado via parametro
- JSON valido no log
"""

from __future__ import annotations

import json
import logging
from typing import Any
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.slow_log import SLOW_THRESHOLD_MS_DEFAULT, SKIP_PATHS, SlowLogMiddleware

SLOW_LOGGER = logging.getLogger("cartorio.slow")


class _CaptureHandler(logging.Handler):
    """Handler de teste que armazena registros em memoria."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def _stub_slow_query_storage(monkeypatch):
    """Evita conexões Redis nas tasks fire-and-forget do middleware."""

    class _InMemorySlowQueryStore:
        async def add_slow_query(self, _query: dict) -> bool:
            return True

    monkeypatch.setattr(
        "app.middleware.slow_log.get_slow_queries_store", lambda: _InMemorySlowQueryStore()
    )


def _capture_logs(handler: _CaptureHandler, level: int = logging.INFO) -> list[dict]:
    """Extrai logs JSON do cartorio.slow logger a partir do handler de captura."""
    out: list[dict] = []
    for record in handler.records:
        if record.name == "cartorio.slow" and record.levelno >= level:
            try:
                payload = json.loads(record.getMessage())
                out.append(payload)
            except (json.JSONDecodeError, TypeError):
                pass
    return out


def _with_capture(app: FastAPI, threshold_ms: int) -> tuple[TestClient, _CaptureHandler]:
    """Cria TestClient + handler de captura para o logger cartorio.slow."""
    client = TestClient(app)
    handler = _CaptureHandler()
    SLOW_LOGGER.handlers.clear()
    SLOW_LOGGER.addHandler(handler)
    SLOW_LOGGER.propagate = False
    SLOW_LOGGER.setLevel(logging.INFO)
    return client, handler


@pytest.fixture(autouse=True)
def _clean_slow_logger():
    """Remove handlers do cartorio.slow apos cada teste."""
    yield
    SLOW_LOGGER.handlers.clear()
    SLOW_LOGGER.propagate = True


def _build_app(threshold_ms: int = 500) -> FastAPI:
    """Cria app de teste com SlowLogMiddleware + endpoint que simula delay."""
    app = FastAPI()
    app.add_middleware(SlowLogMiddleware, threshold_ms=threshold_ms)

    @app.get("/fast")
    async def fast() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/slow")
    async def slow() -> dict[str, Any]:
        import asyncio

        await asyncio.sleep(0.1)
        return {"slow": True}

    return app


class TestSlowLogMiddleware:
    """TDD strict: RED -> GREEN -> commit."""

    def test_request_fast_no_log(self):
        """Request < threshold NAO emite log."""
        app = _build_app(threshold_ms=500)
        client, handler = _with_capture(app, 500)
        response = client.get("/fast")
        assert response.status_code == 200
        assert _capture_logs(handler) == []

    def test_request_slow_emits_info_log(self):
        """Request >= threshold (100ms > 50ms) emite log."""
        app = _build_app(threshold_ms=50)
        client, handler = _with_capture(app, 50)
        response = client.get("/slow")
        assert response.status_code == 200
        logs = _capture_logs(handler)
        assert len(logs) >= 1
        log = logs[0]
        assert log["event"] == "slow_request"
        assert log["method"] == "GET"
        assert log["path"] == "/slow"
        assert log["status_code"] == 200
        assert log["duration_ms"] >= 1
        assert log["threshold_ms"] == 50
        assert "request_id" in log

    def test_skip_paths_no_log(self):
        """Skip paths (/health, /metrics) NAO emitem log mesmo se lentas."""
        app = FastAPI()
        app.add_middleware(SlowLogMiddleware, threshold_ms=1)

        @app.get("/health/live")
        async def health() -> dict[str, Any]:
            import asyncio

            await asyncio.sleep(0.05)
            return {"status": "ok"}

        @app.get("/metrics")
        async def metrics() -> dict[str, Any]:
            import asyncio

            await asyncio.sleep(0.05)
            return {"data": "x"}

        client, handler = _with_capture(app, 1)
        client.get("/health/live")
        client.get("/metrics")
        assert _capture_logs(handler) == []

    def test_log_structure_complete(self):
        """Log contem todos os campos esperados."""
        app = _build_app(threshold_ms=10)
        client, handler = _with_capture(app, 10)
        response = client.get("/slow")
        assert response.status_code == 200
        logs = _capture_logs(handler)
        assert len(logs) >= 1
        log = logs[0]
        required = {
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "threshold_ms",
            "request_id",
        }
        assert required.issubset(log.keys())

    def test_default_threshold_is_500ms(self):
        """Default threshold eh 500ms (SLA P95)."""
        assert SLOW_THRESHOLD_MS_DEFAULT == 500

    def test_skip_paths_constant_includes_health_metrics(self):
        """SKIP_PATHS contem /health, /metrics, /docs."""
        assert "/health" in SKIP_PATHS
        assert "/metrics" in SKIP_PATHS
        assert "/docs" in SKIP_PATHS
        assert "/openapi.json" in SKIP_PATHS

    def test_log_json_valid(self):
        """Mensagem de log eh JSON valido."""
        app = _build_app(threshold_ms=10)
        client, handler = _with_capture(app, 10)
        response = client.get("/slow")
        assert response.status_code == 200
        logs = _capture_logs(handler)
        assert len(logs) >= 1
        assert isinstance(logs[0], dict)

    def test_double_threshold_emits_warning(self):
        """Request >= 2x threshold (100ms >= 2*30=60ms) emite WARNING level."""
        app = _build_app(threshold_ms=30)
        client, handler = _with_capture(app, 30)
        response = client.get("/slow")
        assert response.status_code == 200
        warnings = [
            r for r in handler.records if r.levelno == logging.WARNING and r.name == "cartorio.slow"
        ]
        assert len(warnings) >= 1
