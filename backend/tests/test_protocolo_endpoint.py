"""Testes de integracao dos endpoints /api/v1/protocolo.

Cobre:
- GET /api/v1/protocolo/{numero} (5 cenarios)
- POST /api/v1/protocolo (5+ cenarios)
- Gate LGPD (consentimento obrigatorio)
- PII scrubbing do CPF antes de persistir
- Audit log em todas as mutacoes
- HITL DRAFT (protocolo nunca nasce em EM_ANDAMENTO)
- Formato ANO-SEQUENCIAL do numero (YYYY-NNNNN)
- Idempotencia do cliente por cpf_hash
"""

from __future__ import annotations

import datetime
import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
def cliente_existente(test_engine, test_session_factory):
    """Insere cliente + protocolo ja existentes para teste de GET."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        now = datetime.datetime.utcnow()
        cliente = Cliente(
            cpf_hash="a" * 64,
            nome="Maria Souza",
            consentimento_lgpd=True,
            consentimento_em=now,
        )
        db.add(cliente)
        db.flush()
        protocolo = Protocolo(
            numero="2026-00001",
            cliente_id=cliente.id,
            tipo="certidao_negativa",
            status="DRAFT",
            valor_base=87.50,
            valor_total=87.50,
            tabela_referencia="TABELA_2026_MG",
            prazo_dias=5,
            canal_origem="web",
            created_at=now,
            updated_at=now,
        )
        db.add(protocolo)
        db.commit()
        db.refresh(protocolo)
        return {
            "cliente_id": cliente.id,
            "protocolo_id": protocolo.id,
            "numero": protocolo.numero,
        }


# ============================================================================
# GET /api/v1/protocolo/{numero}
# ============================================================================


def test_get_protocolo_existente_retorna_response_completo(client, cliente_existente):
    """Cenario 1: protocolo existente retorna 200 com historico + proxima_acao."""
    numero = cliente_existente["numero"]
    resp = client.get(f"/api/v1/protocolo/{numero}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Campos obrigatorios
    assert data["numero"] == numero
    assert data["status"] == "DRAFT"
    assert data["etapa_atual"] == "criado"
    assert data["tipo"] == "certidao_negativa"
    assert data["canal_origem"] == "web"
    assert data["valor_base"] == "87.50"
    assert data["valor_total"] == "87.50"
    assert data["tabela_referencia"] == "TABELA_2026_MG"
    assert data["prazo_estimado"] == "5 dias uteis"

    # Cliente - apenas hash, nunca CPF puro
    assert data["cliente"]["nome"] == "Maria Souza"
    assert data["cliente"]["cpf_hash"] == "a" * 64
    assert "123.456" not in data["cliente"]["cpf_hash"]  # nao parece CPF

    # Historico tem pelo menos a etapa de criacao
    assert len(data["historico"]) >= 1
    assert data["historico"][0]["etapa"] == "criado"

    # Proxima acao descreve o HITL
    assert (
        "escrevente" in data["proxima_acao"].lower() or "validacao" in data["proxima_acao"].lower()
    )


def test_get_protocolo_inexistente_retorna_404(client):
    """Cenario 2: protocolo nao encontrado retorna 404 PROTOCOLO_NOT_FOUND."""
    resp = client.get("/api/v1/protocolo/2026-99999")
    assert resp.status_code == 404
    data = resp.json()
    # FastAPI envelopa HTTPException detail no campo `detail`
    detail = data["detail"]
    assert detail["erro"] == "PROTOCOLO_NOT_FOUND"
    assert "2026-99999" in detail["mensagem"]
    assert detail["detalhes"]["numero_consultado"] == "2026-99999"


def test_get_protocolo_formato_invalido_retorna_422(client):
    """Cenario 3: numero fora do formato YYYY-NNNNN retorna 422."""
    # Caracteres nao numericos
    resp = client.get("/api/v1/protocolo/abcdef")
    assert resp.status_code == 422

    # Formato com ano de 5 digitos (invalido)
    resp = client.get("/api/v1/protocolo/10000-00001")
    assert resp.status_code == 422


def test_get_protocolo_grava_audit_log(client, cliente_existente, test_engine):
    """Cenario 4: consulta bem-sucedida grava entrada no audit log."""
    numero = cliente_existente["numero"]
    resp = client.get(f"/api/v1/protocolo/{numero}")
    assert resp.status_code == 200

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        entries = (
            db.execute(
                select(AuditLog)
                .where(AuditLog.action == "protocolo.read")
                .order_by(AuditLog.id.desc())
            )
            .scalars()
            .all()
        )
        assert len(entries) >= 1
        last = entries[0]
        assert last.actor_type == "user"
        assert f"protocolo:{cliente_existente['protocolo_id']}" == last.resource
        assert last.payload["numero"] == numero
        assert last.payload["status"] == "DRAFT"
        assert last.payload["tipo"] == "certidao_negativa"


def test_get_protocolo_nao_existente_grava_audit_seguranca(client, test_engine):
    """Cenario 5: tentativa de leitura de protocolo inexistente tambem e logada
    (importante para auditoria de seguranca contra probing)."""
    antes_count = 0
    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        antes_count = db.query(AuditLog).count()

    resp = client.get("/api/v1/protocolo/2099-00000")
    assert resp.status_code == 404

    with SessionLocal() as db:
        novos = db.query(AuditLog).count()
        assert novos > antes_count
        last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert last.action == "protocolo.read.not_found"
        assert last.payload["result"] == "not_found"


def test_get_protocolo_response_nao_contem_cpf_puro(client, cliente_existente):
    """Cenario bonus: response NUNCA expoe CPF em texto puro (so hash)."""
    resp = client.get(f"/api/v1/protocolo/{cliente_existente['numero']}")
    assert resp.status_code == 200
    text = resp.text
    # Garante que nao ha vestigios de CPF (11 digitos) em texto puro no payload
    assert not re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text)


# ============================================================================
# POST /api/v1/protocolo
# ============================================================================


def _payload_valido(**overrides) -> dict:
    """Helper: payload minimo valido para POST."""
    base = {
        "cliente_cpf": "123.456.789-09",
        "cliente_nome": "Joao da Silva",
        "tipo": "certidao_negativa",
        "canal_origem": "web",
        "consentimento_lgpd": True,
    }
    base.update(overrides)
    return base


def test_post_protocolo_com_consentimento_cria_draft(client):
    """Cenario 1: POST com consentimento_lgpd=true cria protocolo DRAFT (201)."""
    resp = client.post("/api/v1/protocolo", json=_payload_valido())
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["status"] == "criado"
    assert data["estado"] == "DRAFT"  # HITL: nunca EM_ANDAMENTO
    assert re.match(r"^\d{4}-\d{5}$", data["numero"])
    assert isinstance(data["protocolo_id"], int)
    assert "escrevente" in data["proxima_acao"].lower()
    assert isinstance(data["cliente_id"], int)


def test_post_protocolo_sem_consentimento_retorna_lgpd_blocked(client, test_engine):
    """Cenario 2: POST sem consentimento_lgpd=true retorna 422 LGPD_BLOCKED."""
    resp = client.post(
        "/api/v1/protocolo",
        json=_payload_valido(consentimento_lgpd=False),
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["erro"] == "LGPD_BLOCKED"
    assert "LGPD" in detail["mensagem"] or "13.709" in detail["mensagem"]
    assert detail["detalhes"]["consentimento_lgpd_aceito"] is False

    # E loga o bloqueio (LGPD art. 37 - registro de tratamento)
    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        blocked = (
            db.query(AuditLog).filter(AuditLog.action == "protocolo.create.lgpd_blocked").all()
        )
        assert len(blocked) == 1
        assert blocked[0].payload["motivo"] == "consentimento_lgpd=false"


def test_post_protocolo_sem_campo_consentimento_retorna_422(client):
    """Cenario 3: omitir consentimento_lgpd retorna 422 (campo obrigatorio)."""
    payload = _payload_valido()
    payload.pop("consentimento_lgpd")
    resp = client.post("/api/v1/protocolo", json=payload)
    assert resp.status_code == 422


def test_post_protocolo_cpf_e_hasheado_antes_de_persistir(client, test_engine):
    """Cenario 4: CPF puro NUNCA e persistido - apenas hash."""
    cpf_puro = "987.654.321-00"
    resp = client.post(
        "/api/v1/protocolo",
        json=_payload_valido(cliente_cpf=cpf_puro, cliente_nome="Cliente Teste"),
    )
    assert resp.status_code == 201

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        clientes = db.query(Cliente).all()
        assert len(clientes) == 1
        cliente = clientes[0]
        # CPF puro NAO esta no banco
        assert cpf_puro not in cliente.cpf_hash
        assert cpf_puro.replace(".", "").replace("-", "") not in cliente.cpf_hash
        # Apenas hash SHA256
        assert len(cliente.cpf_hash) == 64


def test_post_protocolo_gera_numero_ano_sequencial(client):
    """Cenario 5: numero_protocolo segue formato YYYY-NNNNN (ANO-SEQUENCIAL)."""
    resp1 = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf="111.444.777-35"))
    resp2 = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf="222.555.888-36"))
    resp3 = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf="333.666.999-37"))

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp3.status_code == 201

    ano_atual = str(datetime.datetime.now().year)
    for resp in [resp1, resp2, resp3]:
        numero = resp.json()["numero"]
        assert numero.startswith(ano_atual + "-")
        assert re.match(rf"^{ano_atual}-\d{{5}}$", numero)

    # Sequencial: -00001, -00002, -00003
    nums = [r.json()["numero"] for r in [resp1, resp2, resp3]]
    sufixos = [int(n.split("-")[1]) for n in nums]
    assert sufixos == sorted(sufixos)
    assert len(set(sufixos)) == 3  # todos diferentes


def test_post_protocolo_grava_audit_log_criacao(client, test_engine):
    """Cenario 6: criacao bem-sucedida grava entrada protocolo.create no audit."""
    resp = client.post("/api/v1/protocolo", json=_payload_valido())
    assert resp.status_code == 201
    protocolo_id = resp.json()["protocolo_id"]

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        entries = db.query(AuditLog).filter(AuditLog.action == "protocolo.create").all()
        assert len(entries) == 1
        last = entries[0]
        assert last.actor_type == "bot"
        assert last.resource == f"protocolo:{protocolo_id}"
        assert last.payload["consentimento_lgpd"] is True
        assert last.payload["pii_scrubbed"] is True
        # Hash do CPF no audit, nao o CPF puro
        assert "123.456.789-09" not in last.payload["cpf_hash"]
        assert last.payload["status"] == "DRAFT"


def test_post_protocolo_tipo_invalido_retorna_422(client):
    """Cenario 7: tipo fora da tabela de emolumentos retorna 422 TIPO_INVALIDO."""
    resp = client.post(
        "/api/v1/protocolo",
        json=_payload_valido(tipo="tipo_que_nao_existe"),
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["erro"] == "TIPO_INVALIDO"
    assert "certidao_negativa" in detail["detalhes"]["tipos_validos"]


def test_post_protocolo_idempotente_por_cpf(client, test_engine):
    """Cenario 8: mesmo CPF em 2 chamadas reusa o cliente (1 linha apenas)."""
    cpf = "111.222.333-44"
    r1 = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf=cpf, cliente_nome="Ana"))
    r2 = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf=cpf, cliente_nome="Ana"))

    assert r1.status_code == 201
    assert r2.status_code == 201

    assert r1.json()["cliente_id"] == r2.json()["cliente_id"]  # mesmo cliente
    assert r1.json()["protocolo_id"] != r2.json()["protocolo_id"]  # protocolos diferentes

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        clientes = db.query(Cliente).all()
        assert len(clientes) == 1  # NUNCA duplica cliente


def test_post_protocolo_cpf_sem_pontuacao_e_aceito(client):
    """Cenario 9: CPF sem pontuacao (11 digitos) tambem e aceito."""
    resp = client.post(
        "/api/v1/protocolo",
        json=_payload_valido(cliente_cpf="12345678909"),
    )
    assert resp.status_code == 201


def test_post_protocolo_cpf_invalido_retorna_422(client):
    """Cenario 10: CPF com quantidade de digitos errada retorna 422."""
    resp = client.post(
        "/api/v1/protocolo",
        json=_payload_valido(cliente_cpf="123"),
    )
    assert resp.status_code == 422


def test_post_protocolo_status_sempre_draft_hitl(client, test_engine):
    """Cenario 11: TODOS os protocolos criados pelo endpoint nascem DRAFT.
    Garantia HITL - bot nunca pula validacao humana."""
    for cpf in ["111.111.111-11", "222.222.222-22", "333.333.333-33"]:
        resp = client.post("/api/v1/protocolo", json=_payload_valido(cliente_cpf=cpf))
        assert resp.status_code == 201
        assert resp.json()["estado"] == "DRAFT"

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        protocolos = db.query(Protocolo).all()
        assert len(protocolos) == 3
        for p in protocolos:
            assert p.status == "DRAFT"
            assert p.status != "em_andamento"  # explicito


def test_post_protocolo_tipos_validos_da_tabela(client):
    """Cenario 12: todos os tipos da tabela de emolumentos sao aceitos."""
    from app.services.emolumento import TIPOS_VALIDOS

    cpfs = [
        "111.111.111-11",
        "222.222.222-22",
        "333.333.333-33",
        "444.444.444-44",
        "555.555.555-55",
        "666.666.666-66",
        "777.777.777-77",
        "888.888.888-88",
        "999.999.999-99",
        "123.456.789-09",
        "987.654.321-00",
    ]
    tipos = sorted(TIPOS_VALIDOS)
    assert len(tipos) <= len(cpfs), "ajuste lista de cpfs para cobrir todos os tipos"

    for tipo, cpf in zip(tipos, cpfs):
        resp = client.post(
            "/api/v1/protocolo",
            json=_payload_valido(cliente_cpf=cpf, tipo=tipo),
        )
        assert resp.status_code == 201, f"Falhou para tipo={tipo}: {resp.text}"
        # Snapshot do emolumento foi gravado
        assert resp.json()["estado"] == "DRAFT"
