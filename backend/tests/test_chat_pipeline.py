"""Unit tests for chat_pipeline (Sprint 4 / Turn 51).

Cobre os 10 componentes extraidos do bot Telegram para reuso WhatsApp:
  1. Channel enum (telegram/whatsapp)
  2. InboundMessage / OutboundMessage dataclasses
  3. ChannelAdapter ABC
  4. check_idempotency
  5. check_rate_limit
  6. scrub_pii_3_layers
  7. resume_burst
  8. enqueue_message + fetch_queue
  9. _is_fast_path
 10. hash_content + health_check

Adicionado em 2026-07-09 (lesson 156) — meta: 100% paridade Telegram/WhatsApp.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat_pipeline import (
    Channel,
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    _is_fast_path,
    check_idempotency,
    check_rate_limit,
    enqueue_message,
    fetch_queue,
    hash_content,
    health_check,
    resume_burst,
    scrub_pii_3_layers,
)


def _make_bus_mock() -> MagicMock:
    """Cria bus mockado com set ex=nx + pipeline operations."""
    bus = MagicMock()
    bus.client.set = AsyncMock(return_value=True)
    bus.client.get = AsyncMock(return_value=None)
    bus.client.delete = AsyncMock(return_value=True)
    bus.client.pipeline = MagicMock()
    return bus


# =============================================================================
# T01: Channel enum
# =============================================================================


class TestChannelEnum:
    def test_channel_telegram_value(self) -> None:
        assert Channel.TELEGRAM.value == "telegram"

    def test_channel_whatsapp_value(self) -> None:
        assert Channel.WHATSAPP.value == "whatsapp"

    def test_channel_is_string_enum(self) -> None:
        assert isinstance(Channel.TELEGRAM, str)
        # Pode ser usado em f-string, json, etc.
        assert f"{Channel.TELEGRAM}" == "Channel.TELEGRAM"
        assert Channel.TELEGRAM.value == "telegram"


# =============================================================================
# T02: InboundMessage / OutboundMessage dataclasses
# =============================================================================


class TestMessageDataclasses:
    def test_inbound_message_defaults(self) -> None:
        msg = InboundMessage(channel=Channel.TELEGRAM, sender_id="123")
        assert msg.channel == Channel.TELEGRAM
        assert msg.sender_id == "123"
        assert msg.sender_name == ""
        assert msg.text == ""
        assert msg.update_id == ""
        assert msg.message_ids == []
        assert msg.is_group is False
        assert msg.extra == {}

    def test_outbound_message_defaults(self) -> None:
        out = OutboundMessage(
            channel=Channel.WHATSAPP, recipient_id="55119@s.whatsapp.net", text="Oi"
        )
        assert out.channel == Channel.WHATSAPP
        assert out.recipient_id == "55119@s.whatsapp.net"
        assert out.text == "Oi"
        assert out.keyboard is None
        assert out.react_to_msg_id is None
        assert out.reaction == "thumbsup"
        assert out.parse_mode == "HTML"
        assert out.metadata == {}

    def test_inbound_to_whatsapp(self) -> None:
        msg = InboundMessage(
            channel=Channel.WHATSAPP,
            sender_id="5511999999999@s.whatsapp.net",
            sender_name="Joao",
            text="oi",
            update_id="msg-abc",
            message_ids=["msg-abc"],
            is_group=False,
        )
        assert msg.channel == Channel.WHATSAPP
        assert msg.sender_name == "Joao"
        assert msg.update_id == "msg-abc"


# =============================================================================
# T03: ChannelAdapter ABC
# =============================================================================


class TestChannelAdapter:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            ChannelAdapter()  # type: ignore[abstract]

    def test_must_implement_all_methods(self) -> None:
        class IncompleteAdapter(ChannelAdapter):
            async def send(self, msg: OutboundMessage) -> bool:
                return True

            # typing/react/verify_signature faltando — deve falhar ao instanciar

        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]


# =============================================================================
# T04: check_idempotency
# =============================================================================


class TestCheckIdempotency:
    @pytest.mark.asyncio
    async def test_no_update_id_always_process(self) -> None:
        result = await check_idempotency("", Channel.TELEGRAM)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_bus_returns_false(self) -> None:
        with patch("app.services.chat_pipeline.get_bus", return_value=None):
            result = await check_idempotency("upd-1", Channel.TELEGRAM)
        assert result is False

    @pytest.mark.asyncio
    async def test_first_time_returns_false(self) -> None:
        bus = _make_bus_mock()
        bus.client.set = AsyncMock(return_value=True)  # SETNX succeeded
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            result = await check_idempotency("upd-1", Channel.WHATSAPP)
        assert result is False  # False = processar

    @pytest.mark.asyncio
    async def test_second_time_returns_true(self) -> None:
        bus = _make_bus_mock()
        bus.client.set = AsyncMock(return_value=None)  # SETNX failed = ja existe
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            result = await check_idempotency("upd-1", Channel.WHATSAPP)
        assert result is True  # True = pular

    @pytest.mark.asyncio
    async def test_idempotency_key_format(self) -> None:
        """Key inclui canal para namespacing entre telegram e whatsapp."""
        bus = _make_bus_mock()
        bus.client.set = AsyncMock(return_value=True)
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            await check_idempotency("upd-1", Channel.WHATSAPP)
        # Verifica que key foi construida com canal
        call_args = bus.client.set.call_args
        key = call_args.args[0] if call_args.args else call_args.kwargs.get("key", "")
        assert "whatsapp" in key
        assert "upd-1" in key


# =============================================================================
# T05: check_rate_limit
# =============================================================================


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_no_bus_returns_true(self) -> None:
        with patch("app.services.chat_pipeline.get_bus", return_value=None):
            assert await check_rate_limit("chat-1", Channel.TELEGRAM) is True

    @pytest.mark.asyncio
    async def test_first_request_allowed(self) -> None:
        bus = _make_bus_mock()
        bus.client.set = AsyncMock(return_value=True)
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            assert await check_rate_limit("chat-1", Channel.WHATSAPP) is True

    @pytest.mark.asyncio
    async def test_second_request_blocked(self) -> None:
        bus = _make_bus_mock()
        bus.client.set = AsyncMock(return_value=None)
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            assert await check_rate_limit("chat-1", Channel.WHATSAPP) is False


# =============================================================================
# T06: scrub_pii_3_layers
# =============================================================================


class TestScrubPii3Layers:
    def test_empty_text_returns_zero(self) -> None:
        clean, n = scrub_pii_3_layers("")
        assert clean == ""
        assert n == 0

    def test_none_text_returns_zero(self) -> None:
        clean, n = scrub_pii_3_layers(None)  # type: ignore[arg-type]
        assert clean == ""
        assert n == 0

    def test_cpf_scrubbed(self) -> None:
        clean, n = scrub_pii_3_layers("Meu CPF e 123.456.789-09")
        assert "123.456.789-09" not in clean
        assert n > 0

    def test_email_scrubbed(self) -> None:
        clean, n = scrub_pii_3_layers("Falar com joao@example.com")
        assert "joao@example.com" not in clean

    def test_phone_scrubbed(self) -> None:
        clean, _ = scrub_pii_3_layers("Ligar (34) 99999-0000")
        assert "(34) 99999-0000" not in clean

    def test_clean_text_passes_through(self) -> None:
        text = "Quanto custa um testamento?"
        clean, n = scrub_pii_3_layers(text)
        assert n == 0
        assert "Quanto custa" in clean


# =============================================================================
# T07: resume_burst
# =============================================================================


class TestResumeBurst:
    def test_empty_texts(self) -> None:
        assert resume_burst([]) == ""

    def test_single_text(self) -> None:
        assert resume_burst(["Oi"]) == "Oi"

    def test_two_texts_keeps_both(self) -> None:
        result = resume_burst(["Oi", "Quanto custa?"])
        assert "Oi" in result
        assert "Quanto custa?" in result
        assert "2 mensagens" in result

    def test_three_or_more_returns_resumed(self) -> None:
        result = resume_burst(["Oi", "Tudo bem?", "Quanto custa?"])
        assert "3 mensagens" in result
        assert "Oi" in result
        assert "Quanto custa?" in result


# =============================================================================
# T08: enqueue_message + fetch_queue
# =============================================================================


class TestQueueRoundtrip:
    @pytest.mark.asyncio
    async def test_enqueue_first_returns_true(self) -> None:
        bus = _make_bus_mock()
        pipe = MagicMock()
        pipe.rpush = MagicMock(return_value=MagicMock())
        pipe.llen = MagicMock(return_value=MagicMock(__await__=AsyncMock(return_value=1)))
        pipe.expire = MagicMock(return_value=MagicMock())
        pipe.execute = AsyncMock(return_value=[1, 1, True])
        bus.client.pipeline = MagicMock(return_value=pipe)
        bus.client.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe)
        bus.client.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)

        msg = InboundMessage(
            channel=Channel.TELEGRAM,
            sender_id="123",
            text="oi",
            update_id="upd-1",
            message_ids=["msg-1"],
        )
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            is_first = await enqueue_message(msg)
        # Primeiro elemento na fila -> True
        assert is_first is True

    @pytest.mark.asyncio
    async def test_fetch_queue_no_bus_returns_empty(self) -> None:
        with patch("app.services.chat_pipeline.get_bus", return_value=None):
            result = await fetch_queue(Channel.TELEGRAM, "123")
        assert result == []


# =============================================================================
# T09: _is_fast_path
# =============================================================================


class TestIsFastPath:
    def test_saudacoes_are_fast(self) -> None:
        for txt in [
            "oi",
            "ola",
            "olá",
            "menu",
            "ajuda",
            "help",
            "bom dia",
            "boa tarde",
            "boa noite",
            "hi",
            "hello",
        ]:
            assert _is_fast_path(txt) is True, f"{txt} should be fast"

    def test_long_question_not_fast(self) -> None:
        assert _is_fast_path("Quanto custa um testamento?") is False

    def test_empty_not_fast(self) -> None:
        assert _is_fast_path("") is False

    def test_short_keyword(self) -> None:
        # <= 3 chars considera fast path
        assert _is_fast_path("yo") is True
        assert _is_fast_path("ok") is True

    def test_case_insensitive(self) -> None:
        assert _is_fast_path("OI") is True
        assert _is_fast_path("Ola") is True


# =============================================================================
# T10: hash_content + health_check
# =============================================================================


class TestHashAndHealth:
    def test_hash_content_returns_32_chars(self) -> None:
        h = hash_content("test content")
        assert len(h) == 32

    def test_hash_content_empty(self) -> None:
        assert hash_content("") == ""

    def test_hash_content_deterministic(self) -> None:
        h1 = hash_content("abc")
        h2 = hash_content("abc")
        assert h1 == h2

    def test_hash_content_different_inputs(self) -> None:
        h1 = hash_content("abc")
        h2 = hash_content("xyz")
        assert h1 != h2

    @pytest.mark.asyncio
    async def test_health_check_no_bus(self) -> None:
        with patch("app.services.chat_pipeline.get_bus", return_value=None):
            result = await health_check()
        assert result["pipeline"] == "ok"
        assert result["redis_bus"] is False
        assert "telegram" in result["channels"]
        assert "whatsapp" in result["channels"]

    @pytest.mark.asyncio
    async def test_health_check_with_bus(self) -> None:
        bus = _make_bus_mock()
        bus.client.ping = AsyncMock(return_value=True)
        with patch("app.services.chat_pipeline.get_bus", return_value=bus):
            result = await health_check()
        assert result["redis_bus"] is True
        assert result["version"] == "1.0.0"
