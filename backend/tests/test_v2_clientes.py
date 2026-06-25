"""Testes do GET /api/v2/clientes com cursor pagination Relay-style (A24.2).

Cobre:
1. Listagem basica: retorna lista + cursor de paginacao
2. Cursor pagination: pagina 2 tem resultados corretos, has_next_page correto
3. Filtro por motivo_encerramento: clientes encerrados excluidos por default
4. Ordenacao: por id crescente (estavel pra cursor)
5. Auth: 401 sem credencial (X-API-Key ou JWT)
6. LGPD: response NAO expoe CPF puro (apenas cpf_hash)

Cursor format: opaque base64 de {id_after: int} (Relay-style).
Estabilidade: ordering fixo por id garante cursor consistente.

Usa conftest fixtures: db_session (com monkeypatch do engine global).
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from sqlalchemy.orm import Session  # type: ignore[attr-defined]  # Session re-exported


def _decode_cursor(cursor: str) -> dict:
    """Decodifica cursor opaque (base64 JSON)."""
    padded = cursor + "=" * (-len(cursor) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient que substitui engine e sessao do app por SQLite in-memory."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def sample_clientes(test_session_factory):
    """Insere 5 clientes com ids 1..5."""
    clientes = []
    session = test_session_factory()
    for i in range(1, 6):
        c = Cliente(
            cpf_hash=f"hash_cliente_{i:032d}"[:64],
            nome=f"Cliente {i}",
            email=f"cliente{i}@example.com",
            consentimento_lgpd=True,
            motivo_encerramento=None,
        )
        session.add(c)
        clientes.append(c)
    session.commit()
    for c in clientes:
        session.refresh(c)
    session.close()
    return clientes


# ============================================================================
# Tests
# ============================================================================


def test_v2_clientes_listar_retorna_primeira_pagina(
    client: TestClient, sample_clientes
) -> None:
    """GET /api/v2/clientes retorna primeira pagina com 5 clientes."""
    resp = client.get(
        "/api/v2/clientes",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "edges" in body
    assert "page_info" in body
    assert len(body["edges"]) == 5
    assert body["page_info"]["has_next_page"] is False
    assert body["page_info"]["end_cursor"] is None


def test_v2_clientes_edges_tem_node_e_cursor(
    client: TestClient, sample_clientes
) -> None:
    """Cada edge tem node (dados) + cursor (opaco)."""
    resp = client.get(
        "/api/v2/clientes",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    edge = body["edges"][0]
    assert "node" in edge
    assert "cursor" in edge
    node = edge["node"]
    assert "id" in node
    assert "cpf_hash" in node
    assert "nome" in node
    assert "email" in node


def test_v2_clientes_cursor_pagination_prime_n_itens(
    client: TestClient, sample_clientes
) -> None:
    """first=2 retorna 2 primeiros edges + has_next_page=True + end_cursor."""
    resp = client.get(
        "/api/v2/clientes?first=2",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert len(body["edges"]) == 2
    assert body["edges"][0]["node"]["id"] == 1
    assert body["edges"][1]["node"]["id"] == 2
    assert body["page_info"]["has_next_page"] is True
    assert body["page_info"]["end_cursor"] is not None


def test_v2_clientes_cursor_after_retorna_proxima_pagina(
    client: TestClient, sample_clientes
) -> None:
    """after=cursor retorna itens APOS o cursor (Relay-style)."""
    resp1 = client.get(
        "/api/v2/clientes?first=2",
        headers={"X-API-Key": "a" * 64},
    )
    cursor_2 = resp1.json()["page_info"]["end_cursor"]

    resp2 = client.get(
        f"/api/v2/clientes?first=2&after={cursor_2}",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp2.status_code == 200, resp2.text
    body = resp2.json()

    assert len(body["edges"]) == 2
    assert body["edges"][0]["node"]["id"] == 3
    assert body["edges"][1]["node"]["id"] == 4
    assert body["page_info"]["has_next_page"] is True


def test_v2_clientes_ultima_pagina_sem_next(
    client: TestClient, sample_clientes
) -> None:
    """Ultima pagina: has_next_page=False + end_cursor=None."""
    resp1 = client.get(
        "/api/v2/clientes?first=4",
        headers={"X-API-Key": "a" * 64},
    )
    cursor_4 = resp1.json()["page_info"]["end_cursor"]

    resp2 = client.get(
        f"/api/v2/clientes?first=10&after={cursor_4}",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp2.status_code == 200, resp2.text
    body = resp2.json()

    assert len(body["edges"]) == 1
    assert body["edges"][0]["node"]["id"] == 5
    assert body["page_info"]["has_next_page"] is False
    assert body["page_info"]["end_cursor"] is None


def test_v2_clientes_exclui_encerrados_por_default(
    client: TestClient, db_session: Session, sample_clientes
) -> None:
    """Clientes com motivo_encerramento setado NAO aparecem (LGPD art. 18 VI)."""
    from app.models.cliente import MotivoEncerramento

    cliente_3 = db_session.merge(sample_clientes[2])
    cliente_3.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
    cliente_3.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.get(
        "/api/v2/clientes",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    ids = [e["node"]["id"] for e in body["edges"]]
    assert 3 not in ids
    assert len(body["edges"]) == 4


def test_v2_clientes_inclui_encerrados_se_filtro_explicit(
    client: TestClient, db_session: Session, sample_clientes
) -> None:
    """?include_encerrados=true retorna todos."""
    from app.models.cliente import MotivoEncerramento

    cliente_3 = db_session.merge(sample_clientes[2])
    cliente_3.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
    cliente_3.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.get(
        "/api/v2/clientes?include_encerrados=true",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["edges"]) == 5


def test_v2_clientes_401_sem_auth(client: TestClient) -> None:
    """Sem header X-API-Key -> 401."""
    resp = client.get("/api/v2/clientes")
    assert resp.status_code == 401


def test_v2_clientes_response_nao_expoe_cpf_puro(
    client: TestClient, sample_clientes
) -> None:
    """LGPD art. 37: response NAO expoe CPF puro, apenas cpf_hash."""
    resp = client.get(
        "/api/v2/clientes",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200
    body_text = resp.text

    # NAO deve conter campo "cpf" (apenas cpf_hash)
    assert '"cpf"' not in body_text
    assert '"cpf_hash"' in body_text


def test_v2_clientes_cursor_e_opaco_base64(
    client: TestClient, sample_clientes
) -> None:
    """Cursor eh base64 URL-safe (opaco para o client, decodificavel pelo server)."""
    resp = client.get(
        "/api/v2/clientes?first=1",
        headers={"X-API-Key": "a" * 64},
    )
    assert resp.status_code == 200
    cursor = resp.json()["page_info"]["end_cursor"]

    decoded = _decode_cursor(cursor)
    assert "id_after" in decoded
    assert isinstance(decoded["id_after"], int)