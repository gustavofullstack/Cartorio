"""Testes para endpoints de agendamento."""

import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.agendamento import StatusAgendamento, TipoAtendimento
from app.services.agendamento import AgendamentoService


@pytest.fixture
def test_engine():
    # Force import de TODOS os models para popular Base.metadata
    from sqlalchemy.pool import StaticPool

    # StaticPool = 1 conexao compartilhada (evita "no such table" entre sessoes)
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
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def test_session(test_session_factory):
    """Sessao para testes diretos do service."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cliente_test(test_session):
    """Cria um cliente de teste."""
    from app.services.pii import hash_pii

    cliente = Cliente(
        cpf_hash=hash_pii("12345678909", salt="test-salt"),
        nome="Cliente Teste",
        email="teste@example.com",
        consentimento_lgpd=True,
    )
    test_session.add(cliente)
    test_session.commit()
    test_session.refresh(cliente)
    return cliente


@pytest.fixture
def client(test_engine, test_session_factory):
    """TestClient que substitui engine e sessao do app por SQLite in-memory.

    Usa app.dependency_overrides (recomendado FastAPI) + patch do engine.
    """
    from unittest.mock import patch
    from app.db import get_db

    # IMPORTANTE: patches DEVEM vir ANTES do import do app
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        # Lazy import para pegar patches ativos
        from app.main import app

        # Garante que tabelas existem no engine de teste (idempotente)
        Base.metadata.create_all(test_engine)

        # Override do dependency get_db para retornar sessao de teste
        def _override_get_db():
            db = test_session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db

        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


def test_criar_agendamento_sucesso(test_session, cliente_test):
    """Testa criação de agendamento com sucesso."""
    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Reconhecimento de firma",
        descricao="Documentos: RG, CPF, contrato",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        protocolo_id=None,
        duration_minutes=30,
    )

    assert agendamento.id is not None
    assert agendamento.cliente_id == cliente_test.id
    assert agendamento.status == StatusAgendamento.AGENDADO
    assert agendamento.titulo == "Reconhecimento de firma"
    # Compara data_hora sem timezone para evitar problemas de teste
    assert agendamento.data_hora.replace(tzinfo=None) == data_hora.replace(tzinfo=None)
    # Hash depende do salt, então não testamos valor específico
    assert len(agendamento.cpf_hash) == 64  # SHA-256 hex


def test_criar_agendamento_conflito_horario(test_session, cliente_test):
    """Testa criação de agendamento com conflito de horário."""
    from app.services.agendamento import AgendamentoConflictError

    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    # Cria primeiro agendamento
    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Primeiro agendamento",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        duration_minutes=30,
    )

    # Tenta criar segundo agendamento no mesmo horário
    with pytest.raises(AgendamentoConflictError):
        AgendamentoService.criar_agendamento(
            db=test_session,
            cliente_id=cliente_test.id,
            cliente_cpf="12345678909",
            data_hora=data_hora,
            titulo="Segundo agendamento",
            tipo=TipoAtendimento.NORMAL,
            local="balcao_1",
            duration_minutes=30,
        )


def test_listar_agendamentos_cliente(test_session, cliente_test):
    """Testa listagem de agendamentos de um cliente."""
    data_hora1 = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)
    data_hora2 = datetime.datetime(2026, 7, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    # Cria dois agendamentos
    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora1,
        titulo="Primeiro agendamento",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora2,
        titulo="Segundo agendamento",
        tipo=TipoAtendimento.PRIORITARIO,
        duration_minutes=45,
    )

    # Lista agendamentos
    agendamentos = AgendamentoService.listar_agendamentos_cliente(test_session, cliente_test.id)

    assert len(agendamentos) == 2
    assert agendamentos[0].titulo == "Segundo agendamento"  # Mais recente primeiro
    assert agendamentos[1].titulo == "Primeiro agendamento"


def test_cancelar_agendamento(test_session, cliente_test):
    """Testa cancelamento de agendamento."""
    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    # Cria agendamento
    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Agendamento para cancelar",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    # Cancela agendamento
    agendamento_cancelado = AgendamentoService.cancelar_agendamento(test_session, agendamento.id)

    assert agendamento_cancelado.status == StatusAgendamento.CANCELADO


def test_api_criar_agendamento(client, test_session, cliente_test):
    """Testa endpoint API de criação de agendamento."""

    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    payload = {
        "cliente_id": cliente_test.id,
        "cliente_cpf": "12345678909",
        "data_hora": data_hora.isoformat(),
        "titulo": "Agendamento via API",
        "descricao": "Teste de API",
        "tipo": "normal",
        "local": "balcao_1",
        "duration_minutes": 30,
    }

    response = client.post("/api/v1/agendamento", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Agendamento via API"
    assert data["cliente_id"] == cliente_test.id
    assert data["status"] == "agendado"


def test_api_listar_agendamentos_cliente(client, test_session, cliente_test):
    """Testa endpoint API de listagem de agendamentos."""
    # Cria um agendamento primeiro
    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    payload = {
        "cliente_id": cliente_test.id,
        "cliente_cpf": "12345678909",
        "data_hora": data_hora.isoformat(),
        "titulo": "Agendamento para listar",
        "tipo": "normal",
        "duration_minutes": 30,
    }

    client.post("/api/v1/agendamento", json=payload)

    # Lista agendamentos
    response = client.get(f"/api/v1/agendamento/cliente/{cliente_test.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Agendamento para listar"


def test_api_cancelar_agendamento(client, test_session, cliente_test):
    """Testa endpoint API de cancelamento de agendamento."""
    # Cria um agendamento primeiro
    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    payload = {
        "cliente_id": cliente_test.id,
        "cliente_cpf": "12345678909",
        "data_hora": data_hora.isoformat(),
        "titulo": "Agendamento para cancelar",
        "tipo": "normal",
        "duration_minutes": 30,
    }

    create_response = client.post("/api/v1/agendamento", json=payload)
    agendamento_id = create_response.json()["id"]

    # Cancela agendamento
    cancel_response = client.post(f"/api/v1/agendamento/{agendamento_id}/cancelar")

    assert cancel_response.status_code == 200
    data = cancel_response.json()
    assert data["status"] == "cancelado"


# ============================================================================
# Testes de cobertura para métodos não testados
# ============================================================================


def test_cancelar_agendamento_nao_encontrado(test_session):
    """cancelar_agendamento levanta ValueError se agendamento não existe."""
    from app.services.agendamento import AgendamentoService

    with pytest.raises(ValueError, match="não encontrado"):
        AgendamentoService.cancelar_agendamento(test_session, 99999)


def test_cancelar_agendamento_status_invalido(test_session, cliente_test):
    """cancelar_agendamento levanta ValueError se status não permite cancelamento."""
    from app.services.agendamento import AgendamentoService

    import datetime

    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    from app.models.agendamento import TipoAtendimento

    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Confirmar teste",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    # Cancela primeiro (muda status para CANCELADO)
    AgendamentoService.cancelar_agendamento(test_session, agendamento.id)

    # Tentar cancelar novamente deve falhar (status já CANCELADO)
    with pytest.raises(ValueError, match="não pode ser cancelado"):
        AgendamentoService.cancelar_agendamento(test_session, agendamento.id)


def test_confirmar_agendamento_sucesso(test_session, cliente_test):
    """confirmar_agendamento confirma agendamento com status AGENDADO."""
    from app.services.agendamento import AgendamentoService
    from app.models.agendamento import StatusAgendamento

    import datetime

    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Confirmar teste",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    confirmado = AgendamentoService.confirmar_agendamento(test_session, agendamento.id)
    assert confirmado.status == StatusAgendamento.CONFIRMADO


def test_confirmar_agendamento_nao_encontrado(test_session):
    """confirmar_agendamento levanta ValueError se agendamento não existe."""
    from app.services.agendamento import AgendamentoService

    with pytest.raises(ValueError, match="não encontrado"):
        AgendamentoService.confirmar_agendamento(test_session, 99999)


def test_confirmar_agendamento_status_invalido(test_session, cliente_test):
    """confirmar_agendamento levanta ValueError se status não é AGENDADO."""
    from app.services.agendamento import AgendamentoService

    import datetime

    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)

    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Confirmar status invalido",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    # Cancela primeiro — status CANCELADO, não pode ser confirmado
    AgendamentoService.cancelar_agendamento(test_session, agendamento.id)

    with pytest.raises(ValueError, match="não pode ser confirmado"):
        AgendamentoService.confirmar_agendamento(test_session, agendamento.id)


def test_listar_agendamentos_data(test_session, cliente_test):
    """listar_agendamentos_data retorna agendamentos de uma data específica."""
    import datetime

    data_alvo = datetime.date(2026, 7, 15)

    # Cria agendamento no dia alvo
    agendamento = AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=datetime.datetime(2026, 7, 15, 10, 0, 0, tzinfo=datetime.timezone.utc),
        titulo="Agendamento no dia",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    # Cria agendamento em outro dia (não deve aparecer)
    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=datetime.datetime(2026, 7, 16, 14, 0, 0, tzinfo=datetime.timezone.utc),
        titulo="Agendamento outro dia",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    resultados = AgendamentoService.listar_agendamentos_data(test_session, data_alvo)

    assert len(resultados) == 1
    assert resultados[0].id == agendamento.id
    assert resultados[0].titulo == "Agendamento no dia"


def test_listar_agendamentos_data_com_filtro_local(test_session, cliente_test):
    """listar_agendamentos_data filtra por local quando especificado."""
    import datetime

    data_alvo = datetime.date(2026, 7, 20)

    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=datetime.datetime(2026, 7, 20, 10, 0, 0, tzinfo=datetime.timezone.utc),
        titulo="Balcao 1",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        duration_minutes=30,
    )

    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=datetime.datetime(2026, 7, 20, 11, 0, 0, tzinfo=datetime.timezone.utc),
        titulo="Sala reuniao",
        tipo=TipoAtendimento.NORMAL,
        local="sala_2",
        duration_minutes=30,
    )

    resultados = AgendamentoService.listar_agendamentos_data(
        test_session, data_alvo, local="balcao_1"
    )

    assert len(resultados) == 1
    assert resultados[0].titulo == "Balcao 1"


def test_listar_agendamentos_data_vazio(test_session):
    """listar_agendamentos_data retorna lista vazia se não há agendamentos na data."""
    import datetime

    resultados = AgendamentoService.listar_agendamentos_data(
        test_session, datetime.date(2026, 12, 25)
    )
    assert resultados == []


def test_listar_agendamentos_pendentes_sem_cache(test_session, cliente_test):
    """listar_agendamentos_pendentes retorna agendamentos com status AGENDADO."""
    import datetime

    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=datetime.datetime(2026, 8, 1, 9, 0, 0, tzinfo=datetime.timezone.utc),
        titulo="Pendente 1",
        tipo=TipoAtendimento.NORMAL,
        duration_minutes=30,
    )

    from unittest.mock import patch

    with patch(
        "app.services.agendamento_cache.get_agendamentos_pendentes_cached", return_value=None
    ):
        with patch("app.services.agendamento_cache.set_agendamentos_pendentes_cached"):
            pendentes = AgendamentoService.listar_agendamentos_pendentes(test_session)

    assert len(pendentes) >= 1
    assert pendentes[0]["titulo"] == "Pendente 1"


def test_listar_agendamentos_proximos_vazio(test_session):
    """listar_agendamentos_proximos retorna lista vazia sem agendamentos."""

    from unittest.mock import patch

    with patch(
        "app.services.agendamento_cache.get_agendamentos_proximos_cached", return_value=None
    ):
        with patch("app.services.agendamento_cache.set_agendamentos_proximos_cached"):
            proximos = AgendamentoService.listar_agendamentos_proximos(test_session)

    assert proximos == []
