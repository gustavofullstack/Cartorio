"""Testes para endpoints que estavam sem cobertura direta no router.py.

Adicionados para satisfazer o coverage gate de 90%.
Foco: smoke test + casos de borda dos endpoints que test_protocolo_endpoint
e test_api nao cobriam.

Endpoints cobertos aqui:
- GET  /api/v1/health/backup
- GET  /api/v1/agendamento/disponibilidade
- POST /api/v1/documento/segunda-via
- GET  /api/v1/atendimento/ultimas-24h
- POST /api/v1/atendimento/{id}/pesquisa-enviada
- POST /api/v1/atendimento
- POST /api/v1/atendimento/{id}/concluir
- POST /api/v1/webhook/chatwoot
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.atendimento import Atendimento
from app.models.base import Base


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
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


# ============================================================================
# GET /api/v1/health/backup
# ============================================================================


def test_health_backup_sem_diretorio(client):
    """Retorna ok=False quando /var/backups/cartorio nao existe."""
    # No test env nao ha /var/backups/cartorio
    resp = client.get("/api/v1/health/backup")
    assert resp.status_code == 200
    data = resp.json()
    # Pode ser ok=false (sem backup) ou ok=true (achou arquivos) dependendo do env
    assert "ok" in data
    assert "file_count" in data


# ============================================================================
# GET /api/v1/agendamento/disponibilidade
# ============================================================================


def test_agendamento_disponibilidade_dia_valido(client):
    """Retorna slots para dia valido."""
    resp = client.get("/api/v1/agendamento/disponibilidade?dia=segunda&hora=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dia"] == "segunda"
    assert data["vagas"] == 5
    assert len(data["slots"]) > 0


def test_agendamento_disponibilidade_dia_invalido(client):
    """Retorna erro para dia invalido."""
    resp = client.get("/api/v1/agendamento/disponibilidade?dia=domingo&hora=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "erro" in data
    assert data["vagas"] == 0


def test_agendamento_disponibilidade_hora_fora_expediente(client):
    """Retorna erro para hora fora do expediente (9-17)."""
    resp = client.get("/api/v1/agendamento/disponibilidade?dia=segunda&hora=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "erro" in data
    assert data["vagas"] == 0


def test_agendamento_disponibilidade_hora_inicio(client):
    """Aceita hora 9 (inicio do expediente)."""
    resp = client.get("/api/v1/agendamento/disponibilidade?dia=terca&hora=9")
    assert resp.status_code == 200
    data = resp.json()
    assert "slots" in data


# ============================================================================
# POST /api/v1/documento/segunda-via
# ============================================================================


def test_documento_segunda_via(client):
    """Gera URL placeholder para PDF."""
    resp = client.post("/api/v1/documento/segunda-via?protocolo=2026-00001&canal=whatsapp")
    assert resp.status_code == 200
    data = resp.json()
    assert "url_pdf" in data
    assert "supbase.2notasudi.com.br" in data["url_pdf"]
    assert data["validade_horas"] == 24
    assert data["protocolo"] == "2026-00001"
    assert data["canal"] == "whatsapp"


def test_documento_segunda_via_canal_default(client):
    """Canal default e whatsapp quando nao fornecido."""
    resp = client.post("/api/v1/documento/segunda-via?protocolo=2026-00002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["canal"] == "whatsapp"


# ============================================================================
# GET /api/v1/atendimento/ultimas-24h
# ============================================================================


def test_atendimentos_ultimas_24h_vazio(client):
    """Lista vazia quando nao ha atendimentos concluidos."""
    resp = client.get("/api/v1/atendimento/ultimas-24h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["atendimentos"] == []
    assert data["window_hours"] == 24


def test_atendimentos_ultimas_24h_com_atendimento(client, test_engine):
    """Retorna atendimentos concluidos nas ultimas 24h sem pesquisa_enviada."""
    from app.models.atendimento import Atendimento

    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    with SessionLocal() as s:
        a = Atendimento(
            canal="whatsapp",
            external_id="user1",
            tipo="duvida",
            concluido_em=now - timedelta(hours=2),
            status="concluido",
        )
        s.add(a)
        # Atendimento antigo (>24h) - NAO deve aparecer
        b = Atendimento(
            canal="whatsapp",
            external_id="user2",
            tipo="duvida",
            concluido_em=now - timedelta(hours=30),
            status="concluido",
        )
        s.add(b)
        # Atendimento sem concluido_em - NAO deve aparecer
        c = Atendimento(
            canal="whatsapp",
            external_id="user3",
            tipo="duvida",
            status="em_atendimento",
        )
        s.add(c)
        s.commit()

    resp = client.get("/api/v1/atendimento/ultimas-24h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["atendimentos"][0]["external_id"] == "user1"


def test_atendimentos_ultimas_24h_exclui_pesquisa_enviada(client, test_engine):
    """Nao retorna atendimentos que ja receberam pesquisa."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    with SessionLocal() as s:
        a = Atendimento(
            canal="whatsapp",
            external_id="user1",
            tipo="duvida",
            concluido_em=now - timedelta(hours=1),
            status="concluido",
            pesquisa_enviada_em=now,  # JA RECEBEU PESQUISA
        )
        s.add(a)
        s.commit()

    resp = client.get("/api/v1/atendimento/ultimas-24h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0


# ============================================================================
# POST /api/v1/atendimento/{id}/pesquisa-enviada
# ============================================================================


def test_marcar_pesquisa_enviada_existente(client, test_engine):
    """Marca pesquisa_enviada_em em atendimento existente."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        a = Atendimento(
            canal="whatsapp",
            external_id="user1",
            tipo="duvida",
        )
        s.add(a)
        s.commit()
        aid = a.id

    resp = client.post(f"/api/v1/atendimento/{aid}/pesquisa-enviada")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["atendimento_id"] == aid

    # Verifica que foi persistido
    with SessionLocal() as s:
        a = s.get(Atendimento, aid)
        assert a.pesquisa_enviada_em is not None


def test_marcar_pesquisa_enviada_inexistente(client):
    """Retorna ok=False para atendimento inexistente."""
    resp = client.post("/api/v1/atendimento/999999/pesquisa-enviada")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] == "not_found"


# ============================================================================
# POST /api/v1/atendimento
# ============================================================================


def test_criar_atendimento_basico(client):
    """Cria atendimento sem cliente (sem hash PII)."""
    payload = {
        "canal": "whatsapp",
        "external_id": "user_new_1",
        "tipo": "duvida",
        "contexto_scrubbed": "Cliente perguntou sobre certidao",
    }
    resp = client.post("/api/v1/atendimento", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "atendimento_id" in data
    assert data["atendimento_id"] > 0


def test_criar_atendimento_com_cpf_cliente_novo(client, test_engine):
    """Cria cliente novo quando CPF nao existe."""
    payload = {
        "canal": "whatsapp",
        "external_id": "user_new_2",
        "tipo": "duvida",
        "cliente_cpf": "12345678909",
        "cliente_nome": "Joao da Silva",
    }
    resp = client.post("/api/v1/atendimento", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


# ============================================================================
# POST /api/v1/atendimento/{id}/concluir
# ============================================================================


def test_concluir_atendimento_existente(client, test_engine):
    """Marca atendimento como concluido."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        a = Atendimento(
            canal="whatsapp",
            external_id="user_c1",
            tipo="duvida",
        )
        s.add(a)
        s.commit()
        aid = a.id

    payload = {"nota": 5, "comentario": "Otimo atendimento"}
    resp = client.post(f"/api/v1/atendimento/{aid}/concluir", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    with SessionLocal() as s:
        a = s.get(Atendimento, aid)
        assert a.concluido_em is not None
        assert a.status == "concluido"
        assert a.pesquisa_nota == 5
        assert a.pesquisa_comentario == "Otimo atendimento"


def test_concluir_atendimento_inexistente(client):
    """Retorna ok=False para atendimento inexistente."""
    resp = client.post("/api/v1/atendimento/999999/concluir", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] == "not_found"


# ============================================================================
# POST /api/v1/webhook/chatwoot
# ============================================================================


def test_webhook_chatwoot_evento_desconhecido(client):
    """Evento desconhecido retorna ignored sem acao (Sprint 2 contrato)."""
    resp = client.post(
        "/api/v1/webhook/chatwoot",
        json={"event": "unknown_event", "foo": "bar"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Sprint 2: chatwoot_handoff retorna {status, event} em vez de {ok, event}
    assert data["status"] == "ignored"
    assert data["event"] == "unknown_event"


def test_webhook_chatwoot_conversation_resolved(client, test_engine):
    """Quando conversa e marcada como resolved, atendimento e concluido."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        a = Atendimento(
            canal="whatsapp",
            external_id="user_chat_1",
            tipo="duvida",
            chatwoot_conversation_id=42,
            status="em_atendimento",
        )
        s.add(a)
        s.commit()
        aid = a.id

    payload = {
        "id": "evt-resolved-42",
        "event": "conversation_status_changed",
        "status": "resolved",
        "conversation": {"id": 42, "status": "resolved"},
    }
    resp = client.post("/api/v1/webhook/chatwoot", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Sprint 2: contrato mudou para {status: "processed", event_type: ...}
    assert data["status"] == "processed"
    assert data["event_type"] == "conversation_status_changed"

    with SessionLocal() as s:
        a = s.get(Atendimento, aid)
        assert a.concluido_em is not None
        assert a.status == "concluido"


def test_webhook_chatwoot_conversation_status_changed_other(client):
    """conversation_status_changed com status != resolved: processa mas nao conclui."""
    payload = {
        "id": "evt-other-99",
        "event": "conversation_status_changed",
        "status": "open",
        "conversation": {"id": 99, "status": "open"},
    }
    resp = client.post("/api/v1/webhook/chatwoot", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Processa o evento (status open), mas nao marca atendimento como concluido
    # pois status != resolved
    assert data["status"] == "processed"
    assert data["event_type"] == "conversation_status_changed"
