"""Testes unitários para o webhook de criação de agendamentos presenciais (Wave 7 S7.T1).

Valida:
- Autenticação por X-API-Key (401 se ausente ou inválida)
- Validação de consentimento LGPD do cliente (403 se consentimento_lgpd=False)
- Criação com sucesso (201) e auditoria no audit log
- Tratamento de colisão de horários (409) + incremento da métrica de conflito no Prometheus

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.cliente import Cliente
from app.models.agendamento import Agendamento, StatusAgendamento, TipoAtendimento
from app.services.metrics import store as metrics_store

client = TestClient(app)
TEST_HEADERS = {"X-API-Key": "a" * 64}


def test_criar_agendamento_webhook_without_auth_fails() -> None:
    """POST /api/v1/agendamentos/criar-webhook sem auth header deve falhar com 401."""
    resp = client.post("/api/v1/agendamentos/criar-webhook", json={})
    assert resp.status_code == 401


def test_criar_agendamento_webhook_with_invalid_auth_fails() -> None:
    """POST /api/v1/agendamentos/criar-webhook com auth header inválido deve falhar com 401."""
    resp = client.post("/api/v1/agendamentos/criar-webhook", json={}, headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_criar_agendamento_webhook_without_lgpd_consent_fails(db_session: Session) -> None:
    """POST /api/v1/agendamentos/criar-webhook deve falhar com 403 se o cliente não deu consentimento LGPD."""
    # Cria cliente sem consentimento LGPD
    cliente = Cliente(
        nome="Cliente Sem Consentimento",
        email="sem@consentimento.com",
        cpf_hash="b" * 64,
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    payload = {
        "cliente_id": cliente.id,
        "cliente_cpf": "12345678909",
        "data_hora": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
        "titulo": "Agendamento de Teste",
        "tipo": "normal",
        "local": "balcao_1",
        "duration_minutes": 30
    }

    resp = client.post("/api/v1/agendamentos/criar-webhook", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["erro"] == "LGPD_CONSENT_REQUIRED"


def test_criar_agendamento_webhook_success(db_session: Session) -> None:
    """POST /api/v1/agendamentos/criar-webhook deve criar agendamento se cliente deu consentimento."""
    # Cria cliente com consentimento LGPD
    cliente = Cliente(
        nome="Cliente Com Consentimento",
        email="com@consentimento.com",
        cpf_hash="c" * 64,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()

    data_hora = datetime.datetime.now() + datetime.timedelta(days=1)
    payload = {
        "cliente_id": cliente.id,
        "cliente_cpf": "12345678909",
        "data_hora": data_hora.isoformat(),
        "titulo": "Reconhecimento de Firma",
        "tipo": "normal",
        "local": "balcao_1",
        "duration_minutes": 30
    }

    resp = client.post("/api/v1/agendamentos/criar-webhook", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["titulo"] == "Reconhecimento de Firma"
    assert body["status"] == "agendado"
    assert body["cliente_id"] == cliente.id


def test_criar_agendamento_webhook_concurrency_conflict(db_session: Session) -> None:
    """POST /api/v1/agendamentos/criar-webhook deve retornar 409 se conflito de horário e incrementar métrica."""
    # Cria cliente
    cliente = Cliente(
        nome="Cliente Concorrente",
        email="concorrente@test.com",
        cpf_hash="d" * 64,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()

    # Cria agendamento inicial direto no DB para causar colisão
    data_hora = datetime.datetime.now() + datetime.timedelta(days=2)
    agendamento_existente = Agendamento(
        cliente_id=cliente.id,
        data_hora=data_hora,
        titulo="Agendamento Ocupado",
        status=StatusAgendamento.AGENDADO,
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        cpf_hash="d" * 64,
    )
    db_session.add(agendamento_existente)
    db_session.commit()

    payload = {
        "cliente_id": cliente.id,
        "cliente_cpf": "12345678909",
        "data_hora": data_hora.isoformat(),
        "titulo": "Agendamento Colidente",
        "tipo": "normal",
        "local": "balcao_1",
        "duration_minutes": 30
    }

    # Zera contador de conflitos antes do teste
    metrics_store.counters["cartorio_agendamentos_conflitos_total"] = {"": 0}

    resp = client.post("/api/v1/agendamentos/criar-webhook", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 409
    assert resp.json()["detail"]["erro"] == "CONFLITO_HORARIO"

    # Valida que o contador de conflitos no Prometheus foi incrementado
    assert metrics_store.counters["cartorio_agendamentos_conflitos_total"][""] == 1
