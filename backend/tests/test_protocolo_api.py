"""Testes do endpoint POST /api/v1/protocolo/criar-api.

Specs (Sprint 3 E1.S3.T1 — M1.8 + LGPD P0 #1):
- Endpoint: POST /api/v1/protocolo/criar-api
- Auth: X-API-Key (header)
- Input: cliente_id (int), ato (Enum), valor_snapshot (Decimal 2 casas),
         observacoes (str optional max 500), hitl_draft (bool default True)
- Output: protocolo (CART-YYYY-XXXXXX), cliente_id, status "draft",
          audit_id, created_at, created_by "api"
- LGPD: audit log action="protocolo.created" + cliente.motivo_encerramento check
- HITL: hitl_draft sempre True (escrevente valida)
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo


# ============================================================================
# Fixtures
# ============================================================================


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
    """TestClient com SQLite in-memory + tabelas criadas."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def cliente_existente(test_engine):
    """Insere cliente com ID 1 para testes de cliente_id existente."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        cliente = Cliente(
            id=1,
            cpf_hash="a" * 64,
            nome="Joao da Silva",
            consentimento_lgpd=True,
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente


@pytest.fixture
def api_key(monkeypatch):
    """Seta CARTORIO_API_KEY no settings para os testes."""
    monkeypatch.setenv("CARTORIO_API_KEY", "b" * 64)
    from app.config import settings
    return settings.cartorio_api_key


# ============================================================================
# Tests: Auth
# ============================================================================


def test_criar_api_sem_api_key_retorna_401(client, cliente_existente):
    """Sem header X-API-Key, retorna 401 Unauthorized."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "hitl_draft": True,
        },
    )
    assert resp.status_code == 401
    assert "API key" in resp.text or "X-API-Key" in resp.text or "Unauthorized" in resp.text


def test_criar_api_com_api_key_invalida_retorna_401(client, cliente_existente, monkeypatch):
    """Header X-API-Key com valor errado retorna 401."""
    monkeypatch.setenv("CARTORIO_API_KEY", "b" * 64)
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


# ============================================================================
# Tests: Happy path
# ============================================================================


def test_criar_api_happy_path_retorna_201(client, cliente_existente, api_key, test_engine):
    """Cenario feliz: cria protocolo DRAFT com formato CART-YYYY-XXXXXX."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "150.50",
            "observacoes": "Cliente pediu urgencia",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    # Campos obrigatorios do response
    assert re.match(r"^CART-\d{4}-\d{6}$", data["protocolo"])
    assert data["cliente_id"] == 1
    assert data["status"] == "draft"
    assert data["created_by"] == "api"
    assert data["audit_id"] is not None
    assert data["created_at"] is not None

    # Verifica que gravou no banco
    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        prot = db.query(Protocolo).filter_by(numero=data["protocolo"]).first()
        assert prot is not None
        assert prot.status == "DRAFT"  # HITL: sempre draft
        assert prot.tipo == "escritural"
        assert prot.cliente_id == 1
        assert float(prot.valor_total) == 150.50
        assert prot.canal_origem == "api"


def test_criar_api_grava_audit_log_created(client, cliente_existente, api_key, test_engine):
    """Cenario feliz: cria entrada no audit log com action='protocolo.created'."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "certidao_casamento",
            "valor_snapshot": "87.50",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201
    _ = resp.json()["protocolo"]  # noqa: F841 - we only assert status code

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        entries = db.query(AuditLog).filter_by(action="protocolo.created").all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.actor_type == "api"
        assert entry.actor_id == "api_key"
        assert entry.payload["ato"] == "certidao_casamento"
        assert entry.payload["valor"] == "87.50"
        assert entry.payload["hitl_draft"] is True
        assert entry.payload["cliente_id_hash"].startswith("a")  # hash do cliente 1


# ============================================================================
# Tests: Validacoes
# ============================================================================


def test_criar_api_cliente_nao_existe_retorna_404(client, api_key):
    """cliente_id inexistente retorna 404 CLIENTE_NOT_FOUND."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 99999,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["erro"] == "CLIENTE_NOT_FOUND"
    assert "99999" in detail["mensagem"]


def test_criar_api_valor_negativo_retorna_422(client, cliente_existente, api_key):
    """valor_snapshot negativo retorna 422."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "-100.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


def test_criar_api_valor_zero_retorna_422(client, cliente_existente, api_key):
    """valor_snapshot zero retorna 422 (ato cartorario tem custo > 0)."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "0.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


def test_criar_api_observacoes_maior_500_retorna_422(client, cliente_existente, api_key):
    """observacoes > 500 chars retorna 422."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "observacoes": "x" * 501,
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


def test_criar_api_ato_invalido_retorna_422(client, cliente_existente, api_key):
    """ato fora do Enum retorna 422."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "ato_que_nao_existe",
            "valor_snapshot": "100.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


def test_criar_api_hitl_draft_false_retorna_422(client, cliente_existente, api_key):
    """hitl_draft=False eh proibido (HITL obrigatorio) - retorna 422."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "hitl_draft": False,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


def test_criar_api_hitl_draft_ausente_usa_default_true(client, cliente_existente, api_key, test_engine):
    """hitl_draft omitido assume True (default)."""
    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "escritural",
            "valor_snapshot": "100.00",
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    # Verifica que gravou como DRAFT
    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        prot = db.query(Protocolo).filter_by(cliente_id=1).first()
        assert prot.status == "DRAFT"


# ============================================================================
# Tests: LGPD
# ============================================================================


def test_criar_api_cliente_rejeitado_consent_retorna_lgpd_blocked(
    client, test_engine, api_key
):
    """Cliente com motivo_encerramento = REVOGACAO_CONSENTIMENTO retorna 422 LGPD_BLOCKED."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        from app.models.cliente import MotivoEncerramento

        cliente = Cliente(
            id=2,
            cpf_hash="b" * 64,
            nome="Maria Revogou",
            consentimento_lgpd=False,
            motivo_encerramento=MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
        )
        db.add(cliente)
        db.commit()

    resp = client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 2,
            "ato": "escritural",
            "valor_snapshot": "100.00",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["erro"] == "LGPD_BLOCKED"
    assert "REVOGACAO" in detail["mensagem"].upper() or "consentimento" in detail["mensagem"].lower()


# ============================================================================
# Tests: Numero protocolo formato
# ============================================================================


def test_criar_api_numero_protocolo_formato_cart_yyyy_xxxxxx(
    client, test_engine, api_key
):
    """Numero gerado segue formato CART-YYYY-XXXXXX (CART + 4 ano + 6 seq)."""
    # Insere 2 clientes
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        for cid in [10, 20]:
            db.add(Cliente(
                id=cid,
                cpf_hash=str(cid) * 64,
                nome=f"Cliente {cid}",
                consentimento_lgpd=True,
            ))
        db.commit()

    r1 = client.post(
        "/api/v1/protocolo/criar-api",
        json={"cliente_id": 10, "ato": "escritural", "valor_snapshot": "100.00", "hitl_draft": True},
        headers={"X-API-Key": api_key},
    )
    r2 = client.post(
        "/api/v1/protocolo/criar-api",
        json={"cliente_id": 20, "ato": "escritural", "valor_snapshot": "200.00", "hitl_draft": True},
        headers={"X-API-Key": api_key},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201

    p1 = r1.json()["protocolo"]
    p2 = r2.json()["protocolo"]
    # Formato CART-YYYY-NNNNNN (4 ano + 6 seq)
    assert re.match(r"^CART-\d{4}-\d{6}$", p1), f"p1={p1} nao casa"
    assert re.match(r"^CART-\d{4}-\d{6}$", p2), f"p2={p2} nao casa"
    # Sequenciais diferentes
    assert p1 != p2
    # Mesmo ano
    assert p1.split("-")[1] == p2.split("-")[1]
    # Sequencial incrementa
    seq1 = int(p1.split("-")[2])
    seq2 = int(p2.split("-")[2])
    assert seq2 > seq1