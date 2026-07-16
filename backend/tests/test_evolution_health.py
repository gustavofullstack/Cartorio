"""Testes unitários do endpoint de health check do webhook Evolution (Wave 3 S3.T1).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_evolution_webhook_health_returns_200_and_parses() -> None:
    """GET /api/v1/webhook/evolution/health -> 200 com status ok e parse saudável."""
    resp = client.get("/api/v1/webhook/evolution/health")
    assert resp.status_code == 200
    body = resp.json()

    assert body["status"] == "ok"
    assert body["dual_format_parse"] == "healthy"

    # Valida formato legado extraído
    assert body["legado"]["sender"] == "553499999999"
    assert body["legado"]["text"] == "Teste legado"
    assert body["legado"]["instance"] == "cartorio-2notas"

    # Valida formato moderno extraído
    assert body["moderno"]["sender"] == "553499999999@s.whatsapp.net"
    assert body["moderno"]["text"] == "Teste moderno"
    assert body["moderno"]["instance"] == "cartorio-2notas"
