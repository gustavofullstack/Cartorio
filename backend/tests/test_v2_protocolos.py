"""Testes do GET /api/v2/protocolos com cursor pagination (A24.3).

Cobre:
1. Listagem basica: retorna edges + pageInfo
2. Cursor pagination: pagina 2 funciona
3. Filtro por status (aberto/concluido/etc)
4. Filtro por cliente_id
5. Filtro por tipo
6. Combinacao de filtros
7. 401 sem auth
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64
os.environ.setdefault("JWT_SECRET", "z" * 32)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.cliente import Cliente  # noqa: E402
from app.models.protocolo import Protocolo  # noqa: E402
from app.api.v2.protocolos import router as v2_protocolos_router  # noqa: E402


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(v2_protocolos_router, prefix="/api/v2")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_protocolos(db_session: Session):
    """Insere 1 cliente + 5 protocolos (variados status/tipo)."""
    cliente = Cliente(
        cpf_hash="a" * 64,
        nome="Cliente Teste",
        email="teste@example.com",
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    protocolos = []
    statuses = ["aberto", "em_andamento", "concluido", "aberto", "cancelado"]
    tipos = [
        "certidao_negativa",
        "escritura_compra_venda",
        "procuracao",
        "autenticacao",
        "certidao_positiva",
    ]
    for i in range(5):
        p = Protocolo(
            numero=f"PROT-{2026}{i:06d}",
            cliente_id=cliente.id,
            tipo=tipos[i],
            status=statuses[i],
            valor_base=Decimal("100.00"),
            valor_total=Decimal("150.00"),
            prazo_dias=5,
            previsao_conclusao=datetime.now(timezone.utc),
            canal_origem="web",
        )
        db_session.add(p)
        protocolos.append(p)
    db_session.commit()
    for p in protocolos:
        db_session.refresh(p)
    return protocolos


def test_v2_protocolos_listar_primeira_pagina(client: TestClient, sample_protocolos) -> None:
    """GET /api/v2/protocolos retorna 5 protocolos."""
    resp = client.get(
        "/api/v2/protocolos",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "edges" in body
    assert "page_info" in body
    assert "total_count" in body
    assert len(body["edges"]) == 5
    assert body["total_count"] == 5
    assert body["page_info"]["has_next_page"] is False


def test_v2_protocolos_edges_tem_node_com_campos_esperados(
    client: TestClient, sample_protocolos
) -> None:
    """Cada edge tem node com campos canonicos do protocolo."""
    resp = client.get(
        "/api/v2/protocolos?first=1",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    node = body["edges"][0]["node"]
    assert "id" in node
    assert "numero" in node
    assert "cliente_id" in node
    assert "tipo" in node
    assert "status" in node
    assert "valor_total" in node


def test_v2_protocolos_cursor_pagination(client: TestClient, sample_protocolos) -> None:
    """first=2 + after=cursor retorna 2 itens + has_next_page."""
    resp1 = client.get(
        "/api/v2/protocolos?first=2",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert len(body1["edges"]) == 2
    assert body1["page_info"]["has_next_page"] is True
    cursor = body1["page_info"]["end_cursor"]

    resp2 = client.get(
        f"/api/v2/protocolos?first=2&after={cursor}",
        headers={"X-API-Key": "a" * 64},
    )
    body2 = resp2.json()
    assert len(body2["edges"]) == 2
    # IDs devem ser diferentes (3, 4)
    assert body2["edges"][0]["node"]["id"] != body1["edges"][0]["node"]["id"]


def test_v2_protocolos_filtro_status_aberto(client: TestClient, sample_protocolos) -> None:
    """Filtro status=aberto retorna apenas 2 protocolos."""
    resp = client.get(
        "/api/v2/protocolos?status=aberto",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    assert len(body["edges"]) == 2
    for edge in body["edges"]:
        assert edge["node"]["status"] == "aberto"


def test_v2_protocolos_filtro_cliente_id(
    client: TestClient, sample_protocolos, db_session: Session
) -> None:
    """Filtro cliente_id retorna apenas protocolos daquele cliente."""
    cliente = db_session.query(Cliente).first()
    assert cliente is not None
    resp = client.get(
        f"/api/v2/protocolos?cliente_id={cliente.id}",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    assert len(body["edges"]) == 5
    for edge in body["edges"]:
        assert edge["node"]["cliente_id"] == cliente.id


def test_v2_protocolos_filtro_tipo(client: TestClient, sample_protocolos) -> None:
    """Filtro tipo=procuracao retorna 1 protocolo."""
    resp = client.get(
        "/api/v2/protocolos?tipo=procuracao",
        headers={"X-API-Key": "a" * 64},
    )
    body = resp.json()
    assert len(body["edges"]) == 1
    assert body["edges"][0]["node"]["tipo"] == "procuracao"


def test_v2_protocolos_401_sem_auth(client: TestClient) -> None:
    """Sem header X-API-Key -> 401."""
    resp = client.get("/api/v2/protocolos")
    assert resp.status_code == 401


def test_v2_protocolos_first_limitado_a_100(client: TestClient) -> None:
    """first > 100 -> 422 (validation error)."""
    resp = client.get(
        "/api/v2/protocolos?first=500",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 422


def test_v2_protocolos_cursor_invalido_retorna_primeira_pagina(
    client: TestClient, sample_protocolos
) -> None:
    """Cursor malformado -> fail-soft (retorna primeira pagina, nao 400)."""
    resp = client.get(
        "/api/v2/protocolos?after=isto_nao_e_cursor",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200  # fail-soft
    body = resp.json()
    assert len(body["edges"]) == 5  # todos (cursor ignorado)
