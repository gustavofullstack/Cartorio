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
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.slow_log import SLOW_THRESHOLD_MS_DEFAULT, SKIP_PATHS, SlowLogMiddleware


def _build_app(threshold_ms: int = 500) -> tuple[FastAPI, MagicMock]:
    """Cria app de teste com SlowLogMiddleware + endpoint que simula delay."""
    app = FastAPI()
    handler = MagicMock()
    app.add_middleware(SlowLogMiddleware, threshold_ms=threshold_ms)

    @app.get("/fast")
    async def fast() -> dict:
        return {"ok": True}

    @app.get("/slow")
    async def slow() -> dict:
        import asyncio

        # Aguarda para simular latencia (60ms < 500ms threshold)
        await asyncio.sleep(0.06)
        return {"slow": True}

    return app, handler


def _capture_logs(caplog, level: int = logging.INFO) -> list[dict]:
    """Extrai logs JSON do cartorio.slow logger."""
    out: list[dict] = []
    for record in caplog.records:
        if record.name == "cartorio.slow" and record.levelno >= level:
            try:
                payload = json.loads(record.getMessage())
                out.append(payload)
            except (json.JSONDecodeError, TypeError):
                pass
    return out


class TestSlowLogMiddleware:
    """TDD strict: RED -> GREEN -> commit."""

    def test_request_fast_no_log(self, caplog):
        """Request < threshold NAO emite log."""
        app, _ = _build_app(threshold_ms=500)
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            response = client.get("/fast")

        assert response.status_code == 200
        assert _capture_logs(caplog) == []

    def test_request_slow_emits_info_log(self, caplog):
        """Request >= threshold (60ms < 500ms na verdade) emite log."""
        app, _ = _build_app(threshold_ms=50)  # threshold 50ms
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            response = client.get("/slow")  # 60ms > 50ms

        assert response.status_code == 200
        logs = _capture_logs(caplog)
        assert len(logs) == 1
        log = logs[0]
        assert log["event"] == "slow_request"
        assert log["method"] == "GET"
        assert log["path"] == "/slow"
        assert log["status_code"] == 200
        assert log["duration_ms"] >= 50
        assert log["threshold_ms"] == 50
        assert "request_id" in log

    def test_skip_paths_no_log(self, caplog):
        """Skip paths (/health, /metrics) NAO emitem log mesmo se lentas."""
        app = FastAPI()
        app.add_middleware(SlowLogMiddleware, threshold_ms=1)  # threshold minimo

        @app.get("/health/live")
        async def health() -> dict:
            import asyncio

            await asyncio.sleep(0.05)
            return {"status": "ok"}

        @app.get("/metrics")
        async def metrics() -> dict:
            import asyncio

            await asyncio.sleep(0.05)
            return {"data": "x"}

        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            client.get("/health/live")
            client.get("/metrics")

        assert _capture_logs(caplog) == []

    def test_log_structure_complete(self, caplog):
        """Log contem todos os campos esperados."""
        app, _ = _build_app(threshold_ms=10)
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            response = client.get("/slow")  # 60ms > 10ms

        assert response.status_code == 200
        logs = _capture_logs(caplog)
        assert len(logs) >= 1
        log = logs[0]
        # Campos obrigatorios
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

    def test_log_json_valid(self, caplog):
        """Mensagem de log eh JSON valido."""
        app, _ = _build_app(threshold_ms=10)
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            client.get("/slow")

        for record in caplog.records:
            if record.name == "cartorio.slow":
                # Deve parsear como JSON sem erro
                json.loads(record.getMessage())

    def test_double_threshold_emits_warning(self, caplog):
        """Request >= 2x threshold emite WARNING level."""
        app, _ = _build_app(threshold_ms=30)  # threshold 30ms
        client = TestClient(app)

        with caplog.at_level(logging.INFO, logger="cartorio.slow"):
            client.get("/slow")  # 60ms >= 2*30=60ms

        # Deve ter pelo menos 1 WARNING
        warnings = [
            r for r in caplog.records if r.levelno == logging.WARNING and r.name == "cartorio.slow"
        ]
        assert len(warnings) >= 1
