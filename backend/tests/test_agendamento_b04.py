"""Testes TDD para SQUAD A B0.4 - Agendamento de Atendimentos (Sprint 4).

Cobre:
- Model Agendamento (SQLAlchemy)
- Service AgendamentoService (criar/listar/cancelar/concluir)
- Endpoints REST /api/v1/agendamento*
- Gate LGPD: CPF hasheado antes de persistir
- Audit log em toda mutacao (LGPD art. 37)
- Conflito de horario (409)
- Cliente/Protocolo nao encontrado (404)
- Conflito de horario entre slots (30min default)
- Transicoes de status (confirmar, cancelar, falta, em_atendimento, concluir)
- Listagem por cliente

TDD strict: RED antes de GREEN. Estes testes devem FALHAR ate o
model + service + schemas + router estarem implementados.

Modified by ZCode/Mavis + Gustavo Almeida (2026-06-25 17:00 BRT)
"""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.cliente import Cliente


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_engine():
    """SQLite in-memory engine para testes isolados."""
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
def db(test_engine, test_session_factory):
    """Sessao de banco para testes diretos do service."""
    SessionLocal = test_session_factory
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient FastAPI com SQLite in-memory."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def cliente_padrao(test_engine, test_session_factory):
    """Insere cliente basico para uso nos testes."""

    SessionLocal = test_session_factory
    with SessionLocal() as s:
        now = datetime.datetime.utcnow()
        cliente = Cliente(
            cpf_hash="a" * 64,
            nome="Joao da Silva",
            consentimento_lgpd=True,
            consentimento_em=now,
        )
        s.add(cliente)
        s.commit()
        s.refresh(cliente)
        return cliente.id


# ============================================================================
# Test 1: Model Agendamento existe e tem campos esperados
# ============================================================================


def test_agendamento_model_existe():
    """Model Agendamento deve ser importavel de app.models.agendamento."""
    from app.models.agendamento import (  # type: ignore[import-not-found]
        Agendamento,
    )

    assert Agendamento.__tablename__ == "agendamentos"
    assert hasattr(Agendamento, "criar")


def test_agendamento_status_enum():
    """StatusAgendamento deve ter os 6 estados esperados."""
    from app.models.agendamento import StatusAgendamento  # type: ignore[import-not-found]

    assert StatusAgendamento.AGENDADO.value == "agendado"
    assert StatusAgendamento.CONFIRMADO.value == "confirmado"
    assert StatusAgendamento.EM_ATENDIMENTO.value == "em_atendimento"
    assert StatusAgendamento.CONCLUIDO.value == "concluido"
    assert StatusAgendamento.CANCELADO.value == "cancelado"
    assert StatusAgendamento.FALTOU.value == "falta"


def test_agendamento_tipo_enum():
    """TipoAtendimento deve ter 3 tipos: NORMAL, PRIORITARIO, URGENTE."""
    from app.models.agendamento import TipoAtendimento  # type: ignore[import-not-found]

    assert TipoAtendimento.NORMAL.value == "normal"
    assert TipoAtendimento.PRIORITARIO.value == "prioritario"
    assert TipoAtendimento.URGENTE.value == "urgente"


# ============================================================================
# Test 2: Service criar_agendamento - Happy Path
# ============================================================================


def test_criar_agendamento_happy_path(db, cliente_padrao):
    """Service deve criar agendamento com validacoes basicas."""
    from app.models.agendamento import TipoAtendimento  # type: ignore[import-not-found]
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    data_hora = datetime.datetime(2026, 7, 1, 10, 0, 0)
    agendamento = AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",  # CPF valido
        data_hora=data_hora,
        titulo="Reconhecimento de firma",
        descricao="Documento XYZ",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
    )

    assert agendamento.id is not None
    assert agendamento.cliente_id == cliente_padrao
    assert agendamento.titulo == "Reconhecimento de firma"
    # status pode vir como str (do DB) ou enum
    status_value = (
        agendamento.status.value
        if hasattr(agendamento.status, "value")
        else agendamento.status
    )
    assert status_value == "agendado"
    # LGPD: CPF deve estar hasheado, NAO em texto puro
    assert agendamento.cpf_hash != "52998224725"
    assert len(agendamento.cpf_hash) == 64  # SHA256 hex


def test_criar_agendamento_com_protocolo(db, cliente_padrao):
    """Service deve aceitar protocolo_id quando existir."""
    from app.models.protocolo import Protocolo  # type: ignore[import-not-found]
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    # Cria protocolo com TODOS campos NOT NULL preenchidos
    protocolo = Protocolo(
        numero="2026-00001",
        cliente_id=cliente_padrao,
        tipo="certidao_negativa",
        status="draft",
        canal_origem="balcao",
    )
    db.add(protocolo)
    db.commit()
    db.refresh(protocolo)

    data_hora = datetime.datetime(2026, 7, 1, 11, 0, 0)
    agendamento = AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Assinatura de protocolo",
        protocolo_id=protocolo.id,
    )

    assert agendamento.protocolo_id == protocolo.id


# ============================================================================
# Test 3: Service - Erros de validacao
# ============================================================================


def test_criar_agendamento_cliente_nao_existe(db):
    """Deve levantar ClienteNotFoundError quando cliente_id nao existe."""
    from app.services.agendamento import (  # type: ignore[import-not-found]
        AgendamentoService,
        ClienteNotFoundError,
    )

    with pytest.raises(ClienteNotFoundError):
        AgendamentoService.criar_agendamento(
            db,
            cliente_id=99999,
            cliente_cpf="52998224725",
            data_hora=datetime.datetime(2026, 7, 1, 12, 0, 0),
            titulo="Teste",
        )


def test_criar_agendamento_protocolo_nao_existe(db, cliente_padrao):
    """Deve levantar ProtocoloNotFoundError quando protocolo_id nao existe."""
    from app.services.agendamento import (  # type: ignore[import-not-found]
        AgendamentoService,
        ProtocoloNotFoundError,
    )

    with pytest.raises(ProtocoloNotFoundError):
        AgendamentoService.criar_agendamento(
            db,
            cliente_id=cliente_padrao,
            cliente_cpf="52998224725",
            data_hora=datetime.datetime(2026, 7, 1, 13, 0, 0),
            titulo="Teste",
            protocolo_id=99999,
        )


def test_criar_agendamento_conflito_horario(db, cliente_padrao):
    """Deve levantar AgendamentoConflictError quando ja existe agendamento sobreposto."""
    from app.services.agendamento import (  # type: ignore[import-not-found]
        AgendamentoConflictError,
        AgendamentoService,
    )

    data_hora = datetime.datetime(2026, 7, 1, 14, 0, 0)

    # Primeiro agendamento - deve funcionar
    AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Primeiro",
    )

    # Segundo agendamento sobreposto - deve falhar
    with pytest.raises(AgendamentoConflictError):
        AgendamentoService.criar_agendamento(
            db,
            cliente_id=cliente_padrao,
            cliente_cpf="52998224725",
            data_hora=data_hora + datetime.timedelta(minutes=10),
            titulo="Sobreposto",
        )


def test_criar_agendamento_conflito_local_diferente_ok(db, cliente_padrao):
    """Agendamentos em locais diferentes nao devem conflitar."""
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    data_hora = datetime.datetime(2026, 7, 1, 15, 0, 0)

    AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Balcao 1",
        local="balcao_1",
    )

    # Mesmo horario, local diferente = OK
    agendamento2 = AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Balcao 2",
        local="balcao_2",
    )
    assert agendamento2.id is not None


# ============================================================================
# Test 4: Audit Log LGPD art. 37
# ============================================================================


def test_criar_agendamento_gera_audit_log(db, cliente_padrao):
    """Criar agendamento deve gerar audit log (LGPD art. 37)."""
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    data_hora = datetime.datetime(2026, 7, 1, 17, 0, 0)
    AgendamentoService.criar_agendamento(
        db,
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Com audit",
    )

    # Verifica audit log
    audit_logs = db.execute(select(AuditLog)).scalars().all()
    assert len(audit_logs) >= 1

    # Deve ter action "agendamento.created"
    actions = [log.action for log in audit_logs]
    assert "agendamento.created" in actions

    # CPF em texto puro NAO deve aparecer no payload
    for log in audit_logs:
        if log.action == "agendamento.created":
            payload_str = str(log.payload or "")
            assert "52998224725" not in payload_str  # LGPD!


# ============================================================================
# Test 5: Transicoes de status
# ============================================================================


def test_confirmar_agendamento(db, cliente_padrao):
    """confirmar() deve mudar status de AGENDADO para CONFIRMADO."""
    from app.models.agendamento import (  # type: ignore[import-not-found]
        Agendamento,
        StatusAgendamento,
    )

    data_hora = datetime.datetime(2026, 7, 2, 10, 0, 0)
    ag = Agendamento.criar(
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_hora,
        titulo="Teste confirmar",
    )
    assert ag.status == StatusAgendamento.AGENDADO

    ag.confirmar()
    assert ag.status == StatusAgendamento.CONFIRMADO


def test_cancelar_agendamento(db, cliente_padrao):
    """cancelar() deve funcionar para AGENDADO e CONFIRMADO."""
    from app.models.agendamento import (  # type: ignore[import-not-found]
        Agendamento,
        StatusAgendamento,
    )

    ag = Agendamento.criar(
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=datetime.datetime(2026, 7, 2, 11, 0, 0),
        titulo="Teste cancelar",
    )
    ag.cancelar()
    assert ag.status == StatusAgendamento.CANCELADO


def test_cancelar_apos_concluido_nao_permite(db, cliente_padrao):
    """cancelar() NAO deve funcionar para CONCLUIDO."""
    from app.models.agendamento import (  # type: ignore[import-not-found]
        Agendamento,
        StatusAgendamento,
    )

    ag = Agendamento.criar(
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=datetime.datetime(2026, 7, 2, 12, 0, 0),
        titulo="Teste cancelar concluido",
    )
    ag.confirmar()
    ag.iniciar_atendimento()
    ag.concluir()
    assert ag.status == StatusAgendamento.CONCLUIDO

    ag.cancelar()
    # Status deve permanecer CONCLUIDO (cancelar nao funciona depois de concluido)
    assert ag.status == StatusAgendamento.CONCLUIDO


def test_concluir_define_data_hora_fim(db, cliente_padrao):
    """concluir() deve setar data_hora_fim."""
    from app.models.agendamento import Agendamento  # type: ignore[import-not-found]

    # Data passada (ontem) para que now() > data_hora
    data_passada = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    ag = Agendamento.criar(
        cliente_id=cliente_padrao,
        cliente_cpf="52998224725",
        data_hora=data_passada,
        titulo="Teste concluir",
    )
    ag.confirmar()
    ag.iniciar_atendimento()
    assert ag.data_hora_fim is None

    ag.concluir()
    assert ag.data_hora_fim is not None
    # data_hora_fim deve ser >= data_hora (concluido agora, depois do inicio)
    data_fim_naive = (
        ag.data_hora_fim.replace(tzinfo=None)
        if ag.data_hora_fim.tzinfo
        else ag.data_hora_fim
    )
    data_hora_naive = (
        ag.data_hora.replace(tzinfo=None) if ag.data_hora.tzinfo else ag.data_hora
    )
    assert data_fim_naive >= data_hora_naive


# ============================================================================
# Test 6: Schemas Pydantic
# ============================================================================


def test_agendamento_create_request_schema():
    """Schema AgendamentoCreateRequest deve existir e validar campos."""
    from app.schemas.agendamento import AgendamentoCreateRequest  # type: ignore[import-not-found]

    payload = AgendamentoCreateRequest(
        cliente_id=1,
        cliente_cpf="52998224725",
        data_hora=datetime.datetime(2026, 7, 1, 10, 0, 0),
        titulo="Teste schema",
    )
    assert payload.cliente_id == 1
    assert payload.cliente_cpf == "52998224725"
    assert payload.tipo.value == "normal"  # default


def test_agendamento_response_schema():
    """Schema AgendamentoResponse deve existir e ter campos esperados."""
    from app.schemas.agendamento import AgendamentoResponse  # type: ignore[import-not-found]

    # Validar campos via Pydantic
    assert "id" in AgendamentoResponse.model_fields
    assert "cliente_id" in AgendamentoResponse.model_fields
    assert "data_hora" in AgendamentoResponse.model_fields
    assert "status" in AgendamentoResponse.model_fields


# ============================================================================
# Test 7: Endpoints REST (integracao)
# ============================================================================


def test_post_agendamento_endpoint_201(client, cliente_padrao):
    """POST /api/v1/agendamento deve retornar 201 com agendamento criado."""
    payload = {
        "cliente_id": cliente_padrao,
        "cliente_cpf": "52998224725",
        "data_hora": "2026-07-01T10:00:00",
        "titulo": "Reconhecimento de firma",
        "descricao": "Teste via API",
    }
    response = client.post("/api/v1/agendamento", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["titulo"] == "Reconhecimento de firma"
    assert data["status"] == "agendado"


def test_post_agendamento_endpoint_404_cliente_inexistente(client):
    """POST com cliente_id inexistente deve retornar 404."""
    payload = {
        "cliente_id": 99999,
        "cliente_cpf": "52998224725",
        "data_hora": "2026-07-01T11:00:00",
        "titulo": "Teste 404",
    }
    response = client.post("/api/v1/agendamento", json=payload)
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "CLIENTE_NAO_ENCONTRADO" in str(body["detail"])


def test_post_agendamento_endpoint_409_conflito(client, cliente_padrao):
    """POST com conflito de horario deve retornar 409."""
    payload1 = {
        "cliente_id": cliente_padrao,
        "cliente_cpf": "52998224725",
        "data_hora": "2026-07-01T14:00:00",
        "titulo": "Primeiro",
    }
    response1 = client.post("/api/v1/agendamento", json=payload1)
    assert response1.status_code == 201

    # Segundo com mesmo horario (conflito)
    payload2 = {
        "cliente_id": cliente_padrao,
        "cliente_cpf": "52998224725",
        "data_hora": "2026-07-01T14:10:00",  # sobrepoe
        "titulo": "Conflito",
    }
    response2 = client.post("/api/v1/agendamento", json=payload2)
    assert response2.status_code == 409
    body = response2.json()
    assert "CONFLITO_HORARIO" in str(body["detail"])


def test_get_agendamento_cliente_endpoint(client, cliente_padrao):
    """GET /api/v1/agendamento/cliente/{id} deve listar agendamentos."""
    # Criar 2 agendamentos
    for i in range(2):
        payload = {
            "cliente_id": cliente_padrao,
            "cliente_cpf": "52998224725",
            "data_hora": f"2026-07-0{i+1}T10:00:00",
            "titulo": f"Agendamento {i+1}",
        }
        client.post("/api/v1/agendamento", json=payload)

    response = client.get(f"/api/v1/agendamento/cliente/{cliente_padrao}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


# ============================================================================
# Test 8: Service listar_agendamentos_cliente
# ============================================================================


def test_listar_agendamentos_cliente(db, cliente_padrao):
    """Service deve listar agendamentos de um cliente."""
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    for i in range(3):
        AgendamentoService.criar_agendamento(
            db,
            cliente_id=cliente_padrao,
            cliente_cpf="52998224725",
            data_hora=datetime.datetime(2026, 7, 3, 10 + i, 0, 0),
            titulo=f"Ag {i+1}",
        )

    agendamentos = AgendamentoService.listar_agendamentos_cliente(
        db, cliente_id=cliente_padrao
    )
    assert len(agendamentos) == 3


def test_listar_agendamentos_cliente_vazio(db, cliente_padrao):
    """Cliente sem agendamentos deve retornar lista vazia."""
    from app.services.agendamento import AgendamentoService  # type: ignore[import-not-found]

    agendamentos = AgendamentoService.listar_agendamentos_cliente(
        db, cliente_id=cliente_padrao
    )
    assert agendamentos == []