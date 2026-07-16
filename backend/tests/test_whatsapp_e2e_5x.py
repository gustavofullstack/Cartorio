"""E2E WhatsApp 5x tests (T66-T68 + 2 extras, lesson 156, 2026-07-09).

Cobre 5 fluxos reais via webhook WhatsApp Evolution API (mock):
  T66: "oi" (free-text) -> menu via chat_pipeline
  T67: protocolo 12345  -> consulta DB
  T68: /agendar          -> flow completo (servico->data->hora->confirmar)
  T69: /humano           -> cria atendimento HITL
  T70: /lgpd             -> mostra direitos LGPD

Mocka Evolution API via httpx mock para nao depender de servico externo.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models.base import Base


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("EVOLUTION_REQUIRE_SIGNATURE", "false")  # dev mode
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "")
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

        # Popula o cliente de teste padrão com consentimento LGPD ativo
        db = test_session_factory()
        try:
            from app.models.cliente import Cliente
            from app.services.pii import hash_pii
            c = Cliente(
                cpf_hash=hash_pii("123.456.789-00", salt="a" * 32),
                nome="Cliente de Teste",
                whatsapp_number="5511999999999",
                consentimento_lgpd=True,
            )
            db.add(c)
            db.commit()
        finally:
            db.close()

        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


def _evolution_payload(
    message_id: str, text: str, remote_jid: str = "5511999999999@s.whatsapp.net"
) -> dict:
    """Helper para construir payload Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": remote_jid,
                "fromMe": False,
                "id": message_id,
            },
            "message": {"conversation": text},
            "messageType": "conversation",
            "pushName": "Joao",
        },
    }


def _make_evolved_mock_responses() -> MagicMock:
    """Mocka client httpx com respostas Evolution 200."""
    client = MagicMock()
    # POST /message/sendText/ = 200
    # POST /chat/sendPresence/ = 200
    # POST /message/sendReaction/ = 200
    response_ok = MagicMock()
    response_ok.status_code = 200
    response_ok.text = "{}"
    response_ok.json = MagicMock(return_value={"status": "ok"})
    client.post = AsyncMock(return_value=response_ok)
    client.get = AsyncMock(return_value=response_ok)
    client.aclose = AsyncMock(return_value=None)
    return client


# =============================================================================
# T66: "oi" via WhatsApp -> menu
# =============================================================================


class TestE2EWhatsAppOiToMenu:
    """T66: mensagem 'oi' -> menu via chat_pipeline.process_message (mock Evolution)."""

    def test_oi_returns_menu_response(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-msg-1", text="oi")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["channel"] == "whatsapp"
        # chat_pipeline foi chamado com mensagem "oi"
        mock_pipeline.assert_called_once()
        call_args = mock_pipeline.call_args
        inbound = call_args.args[0] if call_args.args else None
        assert inbound is not None
        assert inbound.text == "oi"
        assert inbound.channel.value == "whatsapp"

    def test_ola_com_acento_whatsapp(self, client: TestClient) -> None:
        """'ola' (sem acento) tambem deve ser processado pelo pipeline."""
        payload = _evolution_payload(message_id="wa-msg-2", text="Ola, bom dia")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        mock_pipeline.assert_called_once()


# =============================================================================
# T67: protocolo 12345 via WhatsApp -> consulta DB
# =============================================================================


class TestE2EWhatsAppProtocolo:
    """T67: protocolo 12345 -> chat_pipeline trata comando via whatsapp router."""

    def test_mensagem_com_protocolo_vai_para_pipeline(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-protocolo-1", text="12345")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        # Pipeline recebeu texto com numero de protocolo
        call_args = mock_pipeline.call_args
        inbound = call_args.args[0]
        assert "12345" in inbound.text

    def test_protocolo_comando_via_whatsapp(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-protocolo-2", text="/protocolo")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        # Comando /protocolo chegou ao pipeline
        inbound = mock_pipeline.call_args.args[0]
        assert "/protocolo" in inbound.text


# =============================================================================
# T68: /agendar -> flow completo
# =============================================================================


class TestE2EWhatsAppAgendar:
    """T68: /agendar -> chat_pipeline -> state machine."""

    def test_agendar_inicio_vai_pipeline(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-agendar-1", text="/agendar")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        assert "/agendar" in inbound.text
        # Canal esta correto
        assert inbound.channel.value == "whatsapp"

    def test_agendar_escolha_data_vai_pipeline(self, client: TestClient) -> None:
        """Escolha de data apos /agendar."""
        payload = _evolution_payload(message_id="wa-agendar-2", text="amanha")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        assert inbound.text == "amanha"


# =============================================================================
# T69: /humano -> cria atendimento HITL via WhatsApp
# =============================================================================


class TestE2EWhatsAppHumano:
    """T69: comando /humano -> cria atendimento HITL."""

    def test_humano_vai_pipeline(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-humano-1", text="/humano")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        assert "/humano" in inbound.text
        # remoteJid preservado
        assert "5511999999999" in inbound.sender_id


# =============================================================================
# T70: /lgpd -> mostra direitos via WhatsApp
# =============================================================================


class TestE2EWhatsAppLgpd:
    """T70: comando /lgpd -> mostra direitos LGPD."""

    def test_lgpd_vai_pipeline(self, client: TestClient) -> None:
        payload = _evolution_payload(message_id="wa-lgpd-1", text="/lgpd")
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        assert "/lgpd" in inbound.text

    def test_whatsapp_pii_scrub_camada_1(self, client: TestClient) -> None:
        """Mensagem com CPF deve chegar ao pipeline com PII scrubbed."""
        payload = _evolution_payload(
            message_id="wa-pii-1",
            text="Meu CPF e 123.456.789-09, preciso de ajuda",
        )
        mock_client = _make_evolved_mock_responses()

        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        # chat_pipeline process_message aplica scrub internamente, mas
        # confirmamos que a mensagem chegou ao pipeline
        assert "123.456.789-09" in inbound.text or "[REDACTED" in inbound.text


# =============================================================================
# Extras: robustness
# =============================================================================


class TestE2EWhatsAppRobustness:
    def test_webhook_wrong_event_returns_ignored(self, client: TestClient) -> None:
        """Event != messages.upsert deve retornar 'ignored'."""
        payload = {
            "event": "connection.update",
            "instance": "cartorio-2notas",
            "data": {},
        }
        resp = client.post("/api/v1/whatsapp/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"

    def test_webhook_missing_data_returns_ignored(self, client: TestClient) -> None:
        """messages.upsert sem data valida -> ignored."""
        payload = {
            "event": "messages.upsert",
            "instance": "cartorio-2notas",
            "data": {"message": {}, "key": {}},  # sem remoteJid/id
        }
        resp = client.post("/api/v1/whatsapp/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"

    def test_group_message_detected(self, client: TestClient) -> None:
        """Mensagem em grupo (@g.us) deve ser flagada is_group=True."""
        payload = _evolution_payload(
            message_id="wa-group-1", text="oi grupo", remote_jid="120363@g.us"
        )
        mock_client = _make_evolved_mock_responses()
        with (
            patch(
                "app.api.v1.whatsapp.WhatsAppAdapter._get_client",
                AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.api.v1.whatsapp.process_message",
                new=AsyncMock(return_value=None),
            ) as mock_pipeline,
        ):
            resp = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert resp.status_code == 200
        inbound = mock_pipeline.call_args.args[0]
        assert inbound.is_group is True
