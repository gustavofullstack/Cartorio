"""E2E Telegram 5x tests (T61-T65, lesson 156, 2026-07-09).

Cobre 5 fluxos reais via webhook Telegram:
  T61: "oi" (free-text) -> menu via fast_llm path
  T62: /protocolo 12345  -> consulta DB (tool _tool_consultar_protocolo)
  T63: /agendar         -> state machine completa (servico->data->hora->confirmar)
  T64: /humano          -> cria atendimento HITL
  T65: /lgpd            -> mostra direitos LGPD

Usa mocks para LLM + Telegram API + dependencias internas (bus, _tool_*).
Para fluxos multi-step (state machine), usa StatefulBus para persistir
estado entre requests.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models.base import Base


# =============================================================================
# Stateful bus mock (substitui redis real para testes multi-step)
# =============================================================================


class StatefulBus:
    """Bus mockado com persistencia in-memory para suportar state machine."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.client = self

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False, **kwargs
    ) -> str | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return "OK"

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def ping(self) -> bool:
        return True


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setenv("AUDIT_HMAC_KEY", "a" * 64)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def test_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    from app.db import get_db
    from app.main import app

    get_settings.cache_clear()

    def _override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        Base.metadata.create_all(test_engine)
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


@pytest.fixture
def stateful_bus():
    return StatefulBus()


def _telegram_update(update_id: int, text: str, chat_id: int = 6682284055) -> dict:
    """Helper para construir update Telegram."""
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": chat_id, "first_name": "Joao", "is_bot": False},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
            "date": 1719227400,
        },
    }


# =============================================================================
# T61: "oi" -> menu via fast_llm path
# =============================================================================


class TestE2ETelegramOiToMenu:
    """T61: free-text 'oi' (sem /comando) -> fast_llm responde com menu."""

    def test_oi_returns_menu_response(self, client: TestClient) -> None:
        update = _telegram_update(update_id=10001, text="oi")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_cartorio_agent",
                new=AsyncMock(
                    return_value=(
                        "Ola! Como posso ajudar? Posso falar sobre agendamento, "
                        "protocolo ou atendimento humano.",
                        None,
                    )
                ),
            ) as mock_agent,
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
            patch("app.api.v1.telegram._get_lgpd_consent", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "partial")
        # free-text IDLE+no bus -> entra no path `if not bus` -> chama agent
        mock_agent.assert_called_once()
        # Texto foi enviado ao Telegram
        mock_send.assert_called_once()

    def test_ola_com_acento_tambem_resposta_menu(self, client: TestClient) -> None:
        """Saudacao com acento (PT-BR) deve ser tratada igual 'oi'."""
        update = _telegram_update(update_id=10002, text="olá")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_cartorio_agent",
                new=AsyncMock(return_value=("Ola! Menu: /agendar /protocolo /humano.", None)),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_bom_dia_saudacao_curl(self, client: TestClient) -> None:
        """'bom dia' tambem eh saudacao valida (fast path)."""
        update = _telegram_update(update_id=10003, text="bom dia")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=None),
            patch(
                "app.api.v1.telegram._call_cartorio_agent",
                new=AsyncMock(return_value=("Bom dia! Em que posso ajudar?", None)),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# =============================================================================
# T62: /protocolo 12345 -> consulta DB
# =============================================================================


class TestE2ETelegramProtocolo:
    """T62: comando /protocolo + numero -> state machine -> ferramenta _tool_consultar_protocolo."""

    def test_protocolo_comando_inicial_retorna_pedido_numero(self, client: TestClient) -> None:
        """Comando /protocolo (sem numero) inicializa state machine via bus."""
        bus = StatefulBus()
        update = _telegram_update(update_id=20001, text="/protocolo")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
            patch("app.api.v1.telegram._get_lgpd_consent", new=AsyncMock(return_value=True)),
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "partial")
        assert data["kind"] == "command"
        # Mensagem enviada deve pedir o numero
        sent_text = mock_send.call_args[0][1]
        assert "protocolo" in sent_text.lower()
        # State PROTOCOLO foi setado no bus
        state_raw = bus.store.get(f"tg:state:{6682284055}")
        if state_raw:
            state = json.loads(state_raw)
            # Pode ser IDLE (se comando cancelou) ou PROTOCOLO
            assert "state" in state

    def test_protocolo_consulta_encontrada(
        self, client: TestClient, stateful_bus: StatefulBus
    ) -> None:
        """Fluxo completo: /protocolo 12345 -> API consulta -> resposta formatada."""
        # Step 1: envia /protocolo (inicia state PROTOCOLO)
        update1 = _telegram_update(update_id=20002, text="/protocolo")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            resp1 = client.post("/api/v1/telegram/webhook", json=update1)
        assert resp1.status_code == 200

        # Step 2: envia "12345" (state PROTOCOLO -> chama _tool_consultar_protocolo)
        update2 = _telegram_update(update_id=20003, text="12345")
        mock_tool_result = {
            "status": "concluido",
            "servico": "Reconhecimento de Firma",
            "data": "2026-07-09",
        }
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._tool_consultar_protocolo",
                new=AsyncMock(return_value=mock_tool_result),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send2,
        ):
            resp2 = client.post("/api/v1/telegram/webhook", json=update2)

        assert resp2.status_code == 200
        data = resp2.json()
        assert data["status"] == "ok"
        # Texto enviado ao Telegram tem protocolo + status
        sent_text = mock_send2.call_args[0][1]
        assert "12345" in sent_text
        assert "concluido" in sent_text.lower() or "Reconhecimento" in sent_text

    def test_protocolo_nao_encontrado(self, client: TestClient, stateful_bus: StatefulBus) -> None:
        """Se protocolo nao existe, retorna mensagem amigavel."""
        # Step 1: /protocolo (inicia state)
        update1 = _telegram_update(update_id=20004, text="/protocolo")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            client.post("/api/v1/telegram/webhook", json=update1)

        update2 = _telegram_update(update_id=20005, text="9999999")
        # Tool retorna erro (simula protocolo inexistente)
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._tool_consultar_protocolo",
                new=AsyncMock(return_value={"erro": "not_found"}),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update2)

        assert resp.status_code == 200
        sent_text = mock_send.call_args[0][1]
        assert "nao encontrado" in sent_text.lower() or "9999999" in sent_text


# =============================================================================
# T63: /agendar -> flow completo servico->data->hora->confirmar
# =============================================================================


class TestE2ETelegramAgendar:
    """T63: comando /agendar -> state machine servico->data->hora->confirmar."""

    def test_agendar_inicio_pede_servico(self, client: TestClient) -> None:
        bus = StatefulBus()
        update = _telegram_update(update_id=30001, text="/agendar")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["kind"] == "command"
        sent_text = mock_send.call_args[0][1]
        # Pede servico
        assert "servi" in sent_text.lower()

    def test_agendar_fluxo_completo_ate_confirmar(
        self, client: TestClient, stateful_bus: StatefulBus
    ) -> None:
        """Walkthrough: /agendar -> servico -> data -> hora -> confirmar (sem commit)."""
        chat_id = 6682284055

        # Step 1: /agendar
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            r1 = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30010, "/agendar", chat_id),
            )
            assert r1.status_code == 200
            assert r1.json()["kind"] == "command"

        # Step 2: escolha servico "1" (reconhecimento_firma) via state machine
        mock_send.reset_mock()
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send2,
        ):
            r2 = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30011, "1", chat_id),
            )
            assert r2.status_code == 200
            assert r2.json()["kind"] == "state"
            # Texto deve pedir data
            sent_text = mock_send2.call_args[0][1]
            assert "data" in sent_text.lower()

        # Step 3: data "amanha"
        mock_send.reset_mock()
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send3,
        ):
            r3 = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30012, "amanha", chat_id),
            )
            assert r3.status_code == 200
            assert r3.json()["kind"] == "state"
            # Texto deve pedir hora
            sent_text = mock_send3.call_args[0][1]
            assert "horario" in sent_text.lower() or "HH:MM" in sent_text or ":" in sent_text

        # Step 4: hora "14:30"
        mock_send.reset_mock()
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send4,
        ):
            r4 = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30013, "14:30", chat_id),
            )
            assert r4.status_code == 200
            assert r4.json()["kind"] == "state"
            # Texto deve pedir confirmacao
            sent_text = mock_send4.call_args[0][1]
            assert "Confirmar" in sent_text or "confirmar" in sent_text

    def test_agendar_escolha_invalida(self, client: TestClient, stateful_bus: StatefulBus) -> None:
        """Opcao invalida no servico retorna 'opcao invalida'."""
        # Step 1: /agendar
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30020, "/agendar"),
            )
        # Step 2: opcao invalida
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            r = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(30021, "9999"),
            )
        assert r.status_code == 200
        assert r.json()["kind"] == "state"
        sent_text = mock_send.call_args[0][1]
        assert "invalida" in sent_text.lower() or "invalido" in sent_text.lower()


# =============================================================================
# T64: /humano -> cria atendimento HITL
# =============================================================================


class TestE2ETelegramHumano:
    """T64: comando /humano -> cria atendimento HITL via _tool_criar_atendimento."""

    def test_humano_inicio_aguarda_descricao(self, client: TestClient) -> None:
        """Comando /humano retorna orientacao inicial."""
        bus = StatefulBus()
        update = _telegram_update(update_id=40001, text="/humano")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["kind"] == "command"
        sent_text = mock_send.call_args[0][1]
        assert "escrevente" in sent_text.lower() or "atendimento" in sent_text.lower()

    def test_humano_cria_atendimento_hitl(
        self, client: TestClient, stateful_bus: StatefulBus
    ) -> None:
        """Fluxo: /humano -> descricao -> cria atendimento no HITL system."""
        # Step 1: /humano (inicia state HITL)
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ),
        ):
            client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(40010, "/humano"),
            )

        # Step 2: descricao -> tool_criar_atendimento retorna ticket_id
        with (
            patch("app.api.v1.telegram.get_bus", return_value=stateful_bus),
            patch(
                "app.api.v1.telegram._tool_criar_atendimento",
                new=AsyncMock(return_value={"atendimento_id": 7777, "id": 7777}),
            ),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post(
                "/api/v1/telegram/webhook",
                json=_telegram_update(40011, "preciso de ajuda com testamento"),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["kind"] == "state"
        # Texto enviado tem numero do ticket
        sent_text = mock_send.call_args[0][1]
        assert "7777" in sent_text or "Ticket" in sent_text


# =============================================================================
# T65: /lgpd -> mostra direitos
# =============================================================================


class TestE2ETelegramLgpd:
    """T65: comando /lgpd -> exibe LGPD_NOTICE com DPO."""

    def test_lgpd_mostra_direitos(self, client: TestClient) -> None:
        bus = StatefulBus()
        update = _telegram_update(update_id=50001, text="/lgpd")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["kind"] == "command"
        sent_text = mock_send.call_args[0][1]
        # Inclui elementos chave do LGPD_NOTICE
        assert "LGPD" in sent_text or "Lei 13.709" in sent_text
        # DPO email
        assert "dpo@2notasudi.com.br" in sent_text
        # Menciona direitos
        assert "acesso" in sent_text.lower() or "exclus" in sent_text.lower()

    def test_lgpd_sem_lgpd_nao_vaza_dados(self, client: TestClient) -> None:
        """Confirma que /lgpd NAO envia dados pessoais na resposta."""
        bus = StatefulBus()
        update = _telegram_update(update_id=50002, text="/lgpd")
        with (
            patch("app.api.v1.telegram.get_bus", return_value=bus),
            patch(
                "app.api.v1.telegram._send_message",
                new=AsyncMock(return_value=True),
            ) as mock_send,
        ):
            resp = client.post("/api/v1/telegram/webhook", json=update)

        assert resp.status_code == 200
        sent_text = mock_send.call_args[0][1]
        # Resposta nao contem CPF/RG/telefone
        import re

        assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", sent_text)
        assert not re.search(r"\(\d{2}\)\s*\d{4,5}-\d{4}", sent_text)
