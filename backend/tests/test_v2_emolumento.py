"""Testes do GET /api/v2/emolumento/tabela (A24.4).

Cobre:
1. Retorna tabela oficial com todos os tipos
2. Cursor pagination Relay-style
3. Filtro only_gratuitos=true retorna apenas gratuitos
4. 401 sem auth (mantem gate de auth mesmo sendo publico conceitualmente)
5. Metadata (tabela_referencia, valido_ate) sempre presente
6. Cada node tem tipo, valor_base, gratuito
"""
from __future__ import annotations

import os

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

from app.api.v2.emolumento import router as v2_emolumento_router  # noqa: E402


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(v2_emolumento_router, prefix="/api/v2")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_v2_emolumento_tabela_retorna_todos_tipos(client: TestClient) -> None:
    """GET /api/v2/emolumento/tabela retorna 10 tipos (placeholder atual)."""
    resp = client.get(
        "/api/v2/emolumento/tabela",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "edges" in body
    assert "page_info" in body
    assert "total_count" in body
    assert "tabela_referencia" in body
    assert "valido_ate" in body
    assert body["tabela_referencia"] == "TABELA_2026_MG"
    assert len(body["edges"]) == 10  # MG 2026 placeholder tem 10 tipos


def test_v2_emolumento_node_tem_campos_canonicos(client: TestClient) -> None:
    """Cada node tem tipo, valor_base (Decimal serializado) e gratuito (bool)."""
    resp = client.get(
        "/api/v2/emolumento/tabela?first=1",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    node = body["edges"][0]["node"]
    assert "tipo" in node
    assert "valor_base" in node
    assert "gratuito" in node
    assert isinstance(node["gratuito"], bool)


def test_v2_emolumento_ordenado_alfabetico(client: TestClient) -> None:
    """Edges ordenados por tipo ASC (cursor estavel)."""
    resp = client.get(
        "/api/v2/emolumento/tabela",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    tipos = [e["node"]["tipo"] for e in body["edges"]]
    assert tipos == sorted(tipos)


def test_v2_emolumento_filtro_gratuitos(client: TestClient) -> None:
    """only_gratuitos=true retorna apenas registros gratuitos (2 tipos)."""
    resp = client.get(
        "/api/v2/emolumento/tabela?only_gratuitos=true",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    # MG 2026 placeholder: registro_nascimento + registro_obito = 2 gratuitos
    assert len(body["edges"]) == 2
    for edge in body["edges"]:
        assert edge["node"]["gratuito"] is True


def test_v2_emolumento_cursor_pagination(client: TestClient) -> None:
    """first=3 retorna 3 itens + has_next_page=True + end_cursor."""
    resp1 = client.get(
        "/api/v2/emolumento/tabela?first=3",
        headers={"X-API-Key": "a" * 64},
    )
    body1 = resp1.json()
    assert len(body1["edges"]) == 3
    assert body1["page_info"]["has_next_page"] is True
    cursor = body1["page_info"]["end_cursor"]

    resp2 = client.get(
        f"/api/v2/emolumento/tabela?first=3&after={cursor}",
        headers={"X-API-Key": "a" * 64},
    )
    body2 = resp2.json()
    assert len(body2["edges"]) == 3
    # Tipos diferentes (alfabetico)
    assert body2["edges"][0]["node"]["tipo"] != body1["edges"][0]["node"]["tipo"]


def test_v2_emolumento_401_sem_auth(client: TestClient) -> None:
    """Sem auth -> 401 (gate X-API-Key mantido)."""
    resp = client.get("/api/v2/emolumento/tabela")
    assert resp.status_code == 401


def test_v2_emolumento_422_first_maior_100(client: TestClient) -> None:
    """first > 100 -> 422."""
    resp = client.get(
        "/api/v2/emolumento/tabela?first=500",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 422


def test_v2_emolumento_cursor_invalido_fail_soft(client: TestClient) -> None:
    """Cursor malformado -> fail-soft (retorna primeira pagina)."""
    resp = client.get(
        "/api/v2/emolumento/tabela?after=isto_nao_e_cursor",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["edges"]) == 10  # todos (cursor ignorado)


def test_v2_emolumento_metadata_sempre_presente(client: TestClient) -> None:
    """tabela_referencia e valido_ate sempre presentes no response."""
    resp = client.get(
        "/api/v2/emolumento/tabela?first=2",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    assert body["tabela_referencia"] == "TABELA_2026_MG"
    assert body["valido_ate"] == "2026-12-31"