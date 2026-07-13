"""T071-T073 + Coverage boost: telegram.py helpers (v22 plan batch 3).

Cobre helper functions nao testadas:
- _send_typing (HTTP POST Telegram sendChatAction)
- _react (HTTP POST Telegram setMessageReaction com map de emojis)
- _enqueue_message (Redis SETEX)
- _get_queued_messages (Redis GET)

Tambem exercita edge cases (bus=None, exception catch) que justificavam
o gap de 19 missing lines (73% -> alvo >=85%).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.v1.telegram import (
    _enqueue_message,
    _get_queued_messages,
    _react,
    _send_typing,
)


# ============================================================================
# _send_typing
# ============================================================================


@pytest.mark.asyncio
async def test_send_typing_success():
    """T071: send_typing retorna True quando Telegram retorna 200."""
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await _send_typing(chat_id=12345)

    assert result is True
    fake_client.post.assert_called_once()
    call_args = fake_client.post.call_args
    assert "sendChatAction" in call_args.args[0]
    assert call_args.kwargs["json"]["chat_id"] == 12345
    assert call_args.kwargs["json"]["action"] == "typing"


@pytest.mark.asyncio
async def test_send_typing_non_200_returns_false():
    """send_typing retorna False se Telegram retorna !=200."""
    fake_response = MagicMock()
    fake_response.status_code = 429
    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await _send_typing(chat_id=12345)

    assert result is False


@pytest.mark.asyncio
async def test_send_typing_exception_returns_false():
    """send_typing retorna False em caso de excecao (network, timeout)."""
    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await _send_typing(chat_id=12345)

    assert result is False


# ============================================================================
# _react (emoji map)
# ============================================================================


@pytest.mark.asyncio
async def test_react_default_thumbsup():
    """T072: _react com reaction='thumbsup' (default) usa emoji 'thumbsup'."""
    fake_client = AsyncMock()
    fake_client.post = AsyncMock()

    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        await _react(chat_id=99, message_id=42)

    call_args = fake_client.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["chat_id"] == 99
    assert payload["message_id"] == 42
    assert payload["reaction"][0]["emoji"] == "👍"


@pytest.mark.asyncio
async def test_react_all_known_emojis():
    """_react aceita todos os emojis canonicos do map interno."""
    known = ["thumbsup", "heart", "smile", "eyes", "check", "cross", "timer"]
    expected_emoji = {
        "thumbsup": "👍",
        "heart": "❤️",
        "smile": "😊",
        "eyes": "👀",
        "check": "✅",
        "cross": "❌",
        "timer": "⏳",
    }

    for reaction_name in known:
        fake_client = AsyncMock()
        fake_client.post = AsyncMock()
        with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            await _react(chat_id=1, message_id=1, reaction=reaction_name)

        payload = fake_client.post.call_args.kwargs["json"]
        assert payload["reaction"][0]["emoji"] == expected_emoji[reaction_name]


@pytest.mark.asyncio
async def test_react_unknown_falls_back_to_thumbsup():
    """_react com reaction desconhecida cai no default thumbsup."""
    fake_client = AsyncMock()
    fake_client.post = AsyncMock()
    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        await _react(chat_id=1, message_id=1, reaction="nao_existe")

    payload = fake_client.post.call_args.kwargs["json"]
    assert payload["reaction"][0]["emoji"] == "👍"


@pytest.mark.asyncio
async def test_react_swallows_exception():
    """_react suprime excecao silenciosamente (best-effort)."""
    with patch("app.api.v1.telegram.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        # Nao deve levantar
        await _react(chat_id=1, message_id=1)


# ============================================================================
# _enqueue_message e _get_queued_messages (Redis queue)
# ============================================================================


@pytest.mark.asyncio
async def test_enqueue_message_bus_none_returns_one():
    """_enqueue_message com bus=None retorna 1 (sentinel: skip queue)."""
    result = await _enqueue_message(bus=None, chat_id=123, text="x", msg_id=1)
    assert result == 1


@pytest.mark.asyncio
async def test_enqueue_message_appends_to_redis_queue():
    """_enqueue_message adiciona na fila Redis (key tg:queue:<chat_id>)."""
    fake_bus = MagicMock()
    fake_bus.client = AsyncMock()
    fake_bus.client.get = AsyncMock(return_value=None)  # queue vazia

    result = await _enqueue_message(bus=fake_bus, chat_id=42, text="hello", msg_id=99)

    assert result == 1
    fake_bus.client.set.assert_called_once()
    set_args = fake_bus.client.set.call_args
    assert set_args.args[0] == "tg:queue:42"
    payload = json.loads(set_args.args[1])  # set(key, value, ex=)
    assert payload[0]["text"] == "hello"
    assert payload[0]["msg_id"] == 99


@pytest.mark.asyncio
async def test_enqueue_message_exception_returns_one():
    """_enqueue_message retorna 1 silenciosamente em caso de exception."""
    fake_bus = MagicMock()
    fake_bus.client = AsyncMock()
    fake_bus.client.get = AsyncMock(side_effect=Exception("redis down"))

    result = await _enqueue_message(bus=fake_bus, chat_id=1, text="x", msg_id=1)

    assert result == 1


@pytest.mark.asyncio
async def test_get_queued_messages_bus_none_returns_empty():
    """_get_queued_messages com bus=None retorna lista vazia."""
    result = await _get_queued_messages(bus=None, chat_id=1)
    assert result == []


@pytest.mark.asyncio
async def test_get_queued_messages_returns_parsed_list():
    """_get_queued_messages retorna mensagens parseadas do Redis."""
    queue_data = json.dumps([{"text": "msg1", "msg_id": 1, "ts": 100.0}])
    fake_bus = MagicMock()
    fake_bus.client = AsyncMock()
    fake_bus.client.get = AsyncMock(return_value=queue_data)

    result = await _get_queued_messages(bus=fake_bus, chat_id=42)

    assert len(result) == 1
    assert result[0]["text"] == "msg1"


@pytest.mark.asyncio
async def test_get_queued_messages_exception_returns_empty():
    """_get_queued_messages retorna [] em caso de exception."""
    fake_bus = MagicMock()
    fake_bus.client = AsyncMock()
    fake_bus.client.get = AsyncMock(side_effect=Exception("fail"))

    result = await _get_queued_messages(bus=fake_bus, chat_id=1)

    assert result == []
