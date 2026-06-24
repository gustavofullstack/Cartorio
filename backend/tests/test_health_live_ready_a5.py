"""Testes A5 — /health/live + /health/ready (liveness/readiness probes)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_live_retorna_200_sem_deps() -> None:
    """/health/live responde 200 sem consultar DB/Redis."""
    client = TestClient(app)
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert data["service"] == "cartorio-api"
    assert "version" in data


def test_health_ready_retorna_200_ou_503_com_checks() -> None:
    """/health/ready checa DB e Redis, retorna 200 ready ou 503 not_ready."""
    client = TestClient(app)
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert data["status"] in ("ready", "not_ready")
    assert "checks" in data
    assert "db" in data["checks"]  # DB sempre checado
