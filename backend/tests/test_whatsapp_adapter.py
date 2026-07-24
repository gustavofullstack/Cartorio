"""Testes unitarios para WhatsAppAdapter (Evolution API bridge).

Cobre 5 aspectos:
  1. send() envia texto via POST /message/sendText/{instance}
  2. typing() envia presence composing/paused
  3. react() mapeia reaction Telegram emoji -> WhatsApp
  4. verify_signature() valida HMAC via evolution_ingest
  5. parse_evolution_payload() normaliza payload Evolution para InboundMessage

Adicionado em 2026-07-09 (lesson 156) — meta: 100% paridade Telegram/WhatsApp.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.whatsapp import (
    ALLOWED_COMMANDS,
    MAX_RESPONSE_LEN,
    WhatsAppAdapter,
    get_adapter,
    parse_evolution_payload,
)
from app.services.chat_pipeline import Channel, OutboundMessage


def _make_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Cria mock de httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = ""
    resp.json = MagicMock(return_value=json_data or {"status": "ok"})
    return resp


# =============================================================================
# T01: send() envia texto via Evolution API
# =============================================================================


class TestWhatsAppSend:
    @pytest.mark.asyncio
    async def test_send_text_success(self) -> None:
        adapter = WhatsAppAdapter(
            base_url="http://fake-evolution:8080",
            api_key="test-key",
            instance="cartorio-test",
        )
        msg = OutboundMessage(
            channel=Channel.WHATSAPP,
            recipient_id="5511999999999@s.whatsapp.net",
            text="Ola! Como posso ajudar?",
        )
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        mock_client.aclose = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send(msg)

        assert result is True
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args.args[0]
        assert "/message/sendText/cartorio-test" in call_url
        # Payload correto
        payload = (
            mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args.args[1]
        )
        assert payload["number"] == "5511999999999"
        assert "Ola" in payload["text"]

    @pytest.mark.asyncio
    async def test_send_with_buttons(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        msg = OutboundMessage(
            channel=Channel.WHATSAPP,
            recipient_id="55119@s.whatsapp.net",
            text="Escolha:",
            keyboard=[
                [{"text": "Sim", "callback_data": "yes"}],
                [{"text": "Nao", "callback_data": "no"}],
            ],
        )
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(201))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send(msg)
        assert result is True
        payload = mock_client.post.call_args.kwargs.get("json")
        assert "buttons" in payload
        assert len(payload["buttons"]) == 2

    @pytest.mark.asyncio
    async def test_send_5xx_returns_false(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        msg = OutboundMessage(
            channel=Channel.WHATSAPP, recipient_id="55119@s.whatsapp.net", text="Oi"
        )
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(500))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_truncates_long_text(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        long_text = "A" * 1500  # > MAX_RESPONSE_LEN
        msg = OutboundMessage(
            channel=Channel.WHATSAPP, recipient_id="55119@s.whatsapp.net", text=long_text
        )
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            await adapter.send(msg)
        payload = mock_client.post.call_args.kwargs.get("json")
        assert len(payload["text"]) <= MAX_RESPONSE_LEN


# =============================================================================
# T02: typing() envia presence composing/paused
# =============================================================================


class TestWhatsAppTyping:
    @pytest.mark.asyncio
    async def test_typing_composing(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.typing("55119@s.whatsapp.net", "composing")
        assert result is True
        payload = mock_client.post.call_args.kwargs.get("json")
        assert payload["presence"] == "composing"
        assert payload["number"] == "55119"

    @pytest.mark.asyncio
    async def test_typing_empty_cancels(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            await adapter.typing("55119@s.whatsapp.net", "")  # cancela
        payload = mock_client.post.call_args.kwargs.get("json")
        assert payload["presence"] == "paused"

    @pytest.mark.asyncio
    async def test_typing_non_blocking_on_error(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.typing("55119@s.whatsapp.net", "composing")
        # Typing eh non-blocking — retorna False mas nao levanta
        assert result is False


# =============================================================================
# T03: react() mapeia Telegram emoji -> WhatsApp
# =============================================================================


class TestWhatsAppReact:
    @pytest.mark.asyncio
    async def test_react_thumbsup_maps(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.react("55119@s.whatsapp.net", "msg-1", "thumbsup")
        assert result is True
        payload = mock_client.post.call_args.kwargs.get("json")
        assert payload["reaction"] == "\U0001f44d"  # 👍
        assert payload["key"]["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_react_unknown_emoji_defaults_thumbsup(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_response(200))
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            await adapter.react("55119@s.whatsapp.net", "msg-2", "banana")
        payload = mock_client.post.call_args.kwargs.get("json")
        # Default eh 👍 quando emoji nao esta no mapa
        assert payload["reaction"] == "\U0001f44d"


# =============================================================================
# T04: verify_signature() valida HMAC via evolution_ingest
# =============================================================================


class TestVerifySignature:
    @pytest.mark.asyncio
    async def test_verify_signature_no_secret_dev_mode(self) -> None:
        """Sem secret configurado, dev mode aceita tudo."""
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        os.environ.pop("EVOLUTION_WEBHOOK_SECRET", None)
        result = await adapter.verify_signature(b'{"test":1}', "fake-sig")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_valid_hmac(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        os.environ["EVOLUTION_WEBHOOK_SECRET"] = "test-secret-123"
        body = b'{"event":"messages.upsert"}'
        # Calcula HMAC valido
        import hashlib
        import hmac as hmac_mod

        sig = hmac_mod.new(b"test-secret-123", body, hashlib.sha256).hexdigest()
        with patch("app.api.v1.whatsapp.validate_evolution_webhook_auth", return_value=True):
            result = await adapter.verify_signature(body, sig)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_invalid_hmac(self) -> None:
        adapter = WhatsAppAdapter(base_url="http://fake:8080", api_key="k", instance="i")
        os.environ["EVOLUTION_WEBHOOK_SECRET"] = "test-secret"
        with patch("app.api.v1.whatsapp.validate_evolution_webhook_auth", return_value=False):
            result = await adapter.verify_signature(b"body", "bad-sig")
        assert result is False


# =============================================================================
# T05: parse_evolution_payload() normaliza payload
# =============================================================================


class TestParseEvolutionPayload:
    def test_parse_message_upsert_conversation(self) -> None:
        payload = {
            "event": "messages.upsert",
            "instance": "cartorio-2notas",
            "data": {
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "fromMe": False,
                    "id": "msg-abc-123",
                },
                "message": {"conversation": "Ola!"},
                "messageType": "conversation",
                "pushName": "Joao",
            },
        }
        result = parse_evolution_payload(payload)
        assert result is not None
        assert result.channel == Channel.WHATSAPP
        assert result.sender_id == "5511999999999@s.whatsapp.net"
        assert result.sender_name == "Joao"
        assert result.text == "Ola!"
        assert result.update_id == "msg-abc-123"
        assert result.is_group is False
        assert result.extra["instance"] == "cartorio-2notas"

    def test_parse_message_upsert_extended_text(self) -> None:
        payload = {
            "event": "messages.upsert",
            "instance": "cartorio-2notas",
            "data": {
                "key": {"remoteJid": "55119@s.whatsapp.net", "fromMe": False, "id": "x"},
                "message": {"extendedTextMessage": {"text": "Quanto custa?"}},
                "messageType": "extendedTextMessage",
                "pushName": "Maria",
            },
        }
        result = parse_evolution_payload(payload)
        assert result is not None
        assert result.text == "Quanto custa?"

    def test_parse_group_message(self) -> None:
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "120363@g.us", "fromMe": False, "id": "g-1"},
                "message": {"conversation": "oi grupo"},
                "messageType": "conversation",
            },
        }
        result = parse_evolution_payload(payload)
        assert result is not None
        assert result.is_group is True

    def test_parse_wrong_event_returns_none(self) -> None:
        payload = {
            "event": "connection.update",
            "data": {},
        }
        result = parse_evolution_payload(payload)
        assert result is None

    def test_parse_missing_data_returns_none(self) -> None:
        payload = {"event": "messages.upsert", "data": {}}
        result = parse_evolution_payload(payload)
        # Sem remoteJid/id → retorna None
        assert result is None


# =============================================================================
# T-Extras: get_adapter + ALLOWED_COMMANDS
# =============================================================================


class TestAdapterSingleton:
    def test_get_adapter_returns_singleton(self) -> None:
        from app.api.v1 import whatsapp as wa_module

        wa_module._adapter_instance = None  # reset
        a1 = get_adapter()
        a2 = get_adapter()
        assert a1 is a2
        assert isinstance(a1, WhatsAppAdapter)

    def test_allowed_commands_matches_telegram(self) -> None:
        """Paridade com Telegram: mesmos 7 comandos."""
        assert "/start" in ALLOWED_COMMANDS
        assert "/menu" in ALLOWED_COMMANDS
        assert "/agendar" in ALLOWED_COMMANDS
        assert "/protocolo" in ALLOWED_COMMANDS
        assert "/humano" in ALLOWED_COMMANDS
        assert "/cancelar" in ALLOWED_COMMANDS
        assert "/lgpd" in ALLOWED_COMMANDS
        assert len(ALLOWED_COMMANDS) == 7
