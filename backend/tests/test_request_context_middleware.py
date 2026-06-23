"""Testes do RequestContextMiddleware.

Cobre:
- Popula request.state.request_id (UUIDv4 unico por request)
- Popula request.state.client_ip respeitando X-Forwarded-For (primeiro hop)
- Fallback para request.client.host quando XFF ausente
- Popula request.state.user_agent do header User-Agent
- Popula request.state.canal quando header X-Canal presente
- Header X-Request-Id de entrada eh propagado se fornecido (idempotencia/tracing)
- request.state.timestamp_iso formato ISO 8601 UTC
- Mantem comportamento normal da rota downstream (200 + body)
- NUNCA bloqueia request: mesmo sem headers, retorna 200
- Ecoa X-Request-Id no response header

Setup minimo: import inline igual test_rate_limit.py (padrao do repo).
"""
from __future__ import annotations

import os
import re
import uuid

# Set test env BEFORE importing app modules (igual conftest.py)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.middleware.request_context import RequestContextMiddleware  # noqa: E402


def _build_app() -> FastAPI:
    """Constroi app minima com middleware registrado."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/_state")
    async def state(request: Request) -> dict:
        return {
            "request_id": getattr(request.state, "request_id", None),
            "client_ip": getattr(request.state, "client_ip", None),
            "user_agent": getattr(request.state, "user_agent", None),
            "canal": getattr(request.state, "canal", None),
            "timestamp_iso": getattr(request.state, "timestamp_iso", None),
        }

    return app


def test_popula_request_id_uuidv4() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.status_code == 200, f"body={resp.text}"
    request_id = resp.json()["request_id"]
    assert request_id is not None
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        request_id,
    ), f"request_id nao eh UUIDv4: {request_id}"


def test_request_id_unico_por_request() -> None:
    app = _build_app()
    client = TestClient(app)
    r1 = client.get("/_state")
    r2 = client.get("/_state")
    assert r1.json()["request_id"] != r2.json()["request_id"]


def test_propagates_incoming_x_request_id() -> None:
    app = _build_app()
    client = TestClient(app)
    incoming = "trace-abc-123"
    resp = client.get("/_state", headers={"X-Request-Id": incoming})
    assert resp.status_code == 200
    assert resp.json()["request_id"] == incoming


def test_client_ip_from_xff_primeiro_hop() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get(
        "/_state",
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1, 10.0.0.2"},
    )
    assert resp.status_code == 200
    # XFF: pegar PRIMEIRO hop (cliente real atras do proxy)
    assert resp.json()["client_ip"] == "203.0.113.7"


def test_client_ip_fallback_request_client_host() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.status_code == 200
    ip = resp.json()["client_ip"]
    assert ip is not None and ip != ""


def test_user_agent_capturado() -> None:
    app = _build_app()
    client = TestClient(app)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Cartorio/0.5"
    resp = client.get("/_state", headers={"User-Agent": ua})
    assert resp.status_code == 200
    assert resp.json()["user_agent"] == ua


def test_user_agent_none_quando_header_ausente() -> None:
    """TestClient injeta User-Agent default; verificamos apenas que o middleware
    captura fielmente o header recebido (ausencia = vazio, mas testclient
    sempre envia 'testclient' como fallback). Verificamos que o UA do testclient
    eh propagado, e que header customizado sobrescreve."""
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    # testclient sempre envia User-Agent: 'testclient' por default
    assert resp.json()["user_agent"] == "testclient"
    # Quando header customizado eh enviado, sobrescreve
    resp2 = client.get("/_state", headers={"User-Agent": ""})
    assert resp2.json()["user_agent"] == ""


def test_canal_capturado_quando_header_presente() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state", headers={"X-Canal": "whatsapp"})
    assert resp.status_code == 200
    assert resp.json()["canal"] == "whatsapp"


def test_canal_none_quando_header_ausente() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.json()["canal"] is None


def test_timestamp_iso_utc_formato_valido() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.status_code == 200
    ts = resp.json()["timestamp_iso"]
    assert ts is not None
    assert ts.startswith(("2025-", "2026-", "2027-"))


def test_nunca_bloqueia_request_ausente_headers() -> None:
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"] is not None
    assert body["client_ip"] is not None


def test_request_id_no_response_header() -> None:
    """Middleware ecoa request_id no response header (X-Request-Id) pra tracing."""
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    assert resp.headers.get("x-request-id") == resp.json()["request_id"]


def test_request_id_valido_como_uuid() -> None:
    """Sanidade: request_id gerado sempre parseia como UUID."""
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/_state")
    rid = resp.json()["request_id"]
    parsed = uuid.UUID(rid)
    assert str(parsed) == rid
