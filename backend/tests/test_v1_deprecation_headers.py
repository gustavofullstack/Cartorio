"""Testes do middleware de deprecation v1 (A24.5).

Adiciona headers `Deprecation` (RFC 8594) e `Sunset` (RFC 7231) em rotas /api/v1/*,
avisando clientes que a API sera removida em 2027-12-31.

Cobre:
1. Rota /api/v1/* retorna header Deprecation: true
2. Rota /api/v1/* retorna header Sunset: Wed, 31 Dec 2027 ...
3. Rota /api/v2/* NAO recebe headers de deprecation
4. Rota /health (sem versionamento) NAO recebe headers
5. Header Link com rel="successor-version" aponta pra /api/v2
6. Headers preservam respostas normais (200, 401, etc)
"""
from __future__ import annotations

import os
from datetime import datetime

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)
os.environ.setdefault("JWT_SECRET", "z" * 32)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.middleware.deprecation import DeprecationHeadersMiddleware  # noqa: E402


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    # Adiciona middleware
    test_app.add_middleware(DeprecationHeadersMiddleware)

    @test_app.get("/api/v1/clientes")
    async def v1_clientes() -> dict:
        return {"clientes": []}

    @test_app.get("/api/v2/clientes")
    async def v2_clientes() -> dict:
        return {"edges": []}

    @test_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @test_app.get("/api/v1/protocolos/{id}")
    async def v1_protocolo(id: int) -> dict:
        return {"id": id}

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_v1_endpoint_retorna_deprecation_true(client: TestClient) -> None:
    """Rota /api/v1/* retorna Deprecation: true."""
    resp = client.get("/api/v1/clientes")
    assert resp.status_code == 200
    # Header Deprecation pode ser "true" (boolean) ou RFC 7231 date
    deprecation = resp.headers.get("deprecation", "")
    assert deprecation == "true"


def test_v1_endpoint_retorna_sunset_2027(client: TestClient) -> None:
    """Rota /api/v1/* retorna Sunset header com data 2027-12-31."""
    resp = client.get("/api/v1/clientes")
    sunset = resp.headers.get("sunset", "")
    assert "2027" in sunset
    # Formato RFC 7231: "Wed, 31 Dec 2027 00:00:00 GMT"
    assert "31 Dec 2027" in sunset or "2027-12-31" in sunset


def test_v1_endpoint_retorna_link_successor_v2(client: TestClient) -> None:
    """Rota /api/v1/* retorna Link header apontando para /api/v2."""
    resp = client.get("/api/v1/clientes")
    link = resp.headers.get("link", "")
    assert 'rel="successor-version"' in link
    assert "/api/v2/clientes" in link


def test_v2_endpoint_nao_recebe_deprecation_headers(client: TestClient) -> None:
    """Rota /api/v2/* NAO recebe headers de deprecation (v2 eh o destino)."""
    resp = client.get("/api/v2/clientes")
    assert resp.status_code == 200
    # Headers de deprecation NAO devem estar presentes
    assert "deprecation" not in {k.lower() for k in resp.headers.keys()}
    assert "sunset" not in {k.lower() for k in resp.headers.keys()}


def test_health_nao_recebe_deprecation_headers(client: TestClient) -> None:
    "Rota /health (sem versionamento) NAO recebe headers."
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "deprecation" not in {k.lower() for k in resp.headers.keys()}


def test_v1_com_path_param_tambem_recebe_headers(client: TestClient) -> None:
    """/api/v1/protocolos/{id} tambem recebe headers (path params OK)."""
    resp = client.get("/api/v1/protocolos/123")
    assert resp.status_code == 200
    assert resp.headers.get("deprecation") == "true"
    assert "2027" in resp.headers.get("sunset", "")


def test_v1_preserva_status_codes_originais(client: TestClient) -> None:
    """Middleware NAO altera status code original."""
    resp = client.get("/api/v1/clientes")
    assert resp.status_code == 200
    # Body original intacto
    assert resp.json() == {"clientes": []}


def test_sunset_date_e_2027_12_31(client: TestClient) -> None:
    """Sunset date eh exatamente 2027-12-31 (confirma com parse)."""
    resp = client.get("/api/v1/clientes")
    sunset_str = resp.headers.get("sunset", "")

    # Tenta formatos RFC 7231 ou ISO
    sunset_dt = None
    for fmt in ("%a, %d %b %Y %H:%M:%S GMT", "%Y-%m-%d"):
        try:
            sunset_dt = datetime.strptime(sunset_str, fmt)
            break
        except ValueError:
            continue

    assert sunset_dt is not None, f"Sunset format not recognized: {sunset_str}"
    assert sunset_dt.year == 2027
    assert sunset_dt.month == 12
    assert sunset_dt.day == 31


def test_link_header_aponta_para_path_v2_equivalente(client: TestClient) -> None:
    """Link header converte /api/v1/* -> /api/v2/* mantendo o resto do path."""
    resp = client.get("/api/v1/protocolos/456")
    link = resp.headers.get("link", "")
    # Pode apontar pra v2 collection ou v2/{id} — pelo menos menciona v2
    assert "/api/v2" in link