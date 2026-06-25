"""Testes para endpoints N8N de agendamento."""

import datetime
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

# Configura API key para testes antes de qualquer import do app
os.environ["CARTORIO_API_KEY"] = "a" * 64  # 64 chars hex lowercase

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.agendamento import TipoAtendimento
from app.services.agendamento import AgendamentoService
from app.services.pii import hash_pii


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
    cliente = Cliente(
        cpf_hash=hash_pii("12345678909", salt="test-salt"),
        nome="Cliente Teste",
        email="teste@example.com",
        consentimento_lgpd=True,
        telegram_chat_id="placeholder",  # placeholder, sobrescrito apos commit
    )
    test_session.add(cliente)
    test_session.commit()
    test_session.refresh(cliente)
    # Apos obter o ID, atualiza telegram_chat_id com o ID real (formato esperado)
    cliente.telegram_chat_id = f"client_{cliente.id}_telegram"
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


def test_api_agendamentos_pendentes(client, test_session, cliente_test):
    """Testa endpoint N8N de agendamentos pendentes."""

    # Cria um agendamento pendente
    data_hora = datetime.datetime(2026, 7, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)
    
    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Agendamento pendente",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        duration_minutes=30,
    )

    # Testa endpoint com API key válida
    response = client.get("/api/v1/agendamento/pendentes", headers={
        "X-API-Key": os.environ["CARTORIO_API_KEY"]
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Agendamento pendente"
    assert data[0]["status"] == "agendado"


def test_api_agendamentos_proximos(client, test_session, cliente_test):
    """Testa endpoint N8N de agendamentos próximos."""

    # Cria um agendamento próximo (dentro de 24 horas)
    agora = datetime.datetime.now(datetime.timezone.utc)
    data_hora = agora + datetime.timedelta(hours=2)  # Daqui a 2 horas
    
    AgendamentoService.criar_agendamento(
        db=test_session,
        cliente_id=cliente_test.id,
        cliente_cpf="12345678909",
        data_hora=data_hora,
        titulo="Agendamento próximo",
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        duration_minutes=30,
    )

    # Testa endpoint com API key válida
    response = client.get("/api/v1/agendamento/proximos", headers={
        "X-API-Key": os.environ["CARTORIO_API_KEY"]
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Agendamento próximo"
    assert data[0]["cliente_telegram_chat_id"] == f"client_{cliente_test.id}_telegram"


def test_api_agendamentos_pendentes_sem_api_key(client):
    """Testa endpoint N8N sem API key (deve falhar)."""
    response = client.get("/api/v1/agendamento/pendentes")
    assert response.status_code == 401


def test_api_agendamentos_proximos_sem_api_key(client):
    """Testa endpoint N8N sem API key (deve falhar)."""
    response = client.get("/api/v1/agendamento/proximos")
    assert response.status_code == 401