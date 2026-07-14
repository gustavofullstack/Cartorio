import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from app.api.v1.telegram import (
    _process_telegram_debounce,
    _handle_callback,
    _handle_command,
    _DEBOUNCE_METADATA,
)


@pytest.mark.asyncio
async def test_extra_coverage_debounce_with_metadata() -> None:
    # Exercita a leitura de metadata do dicionario global
    chat_id = 999888
    _DEBOUNCE_METADATA[chat_id] = {"conv_key": "conv_999888", "user_id": 1234}

    mock_bus = MagicMock()
    mock_pipe = AsyncMock()
    raw_queue = json.dumps([{"text": "Ola bot", "msg_id": 111}])
    mock_pipe.execute = AsyncMock(return_value=[raw_queue, True, True])
    mock_bus.client.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_bus.client.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch("app.api.v1.telegram.DEBOUNCE_WINDOW", 0.001):
            with patch(
                "app.api.v1.telegram._call_cartorio_agent",
                AsyncMock(return_value=("Resposta", None)),
            ):
                with patch(
                    "app.api.v1.telegram._send_message", AsyncMock(return_value=True)
                ) as mock_send:
                    with patch("app.api.v1.telegram._react", AsyncMock(return_value=True)):
                        await _process_telegram_debounce(chat_id)
                        assert mock_send.called


@pytest.mark.asyncio
async def test_extra_coverage_handle_callback_chat_id() -> None:
    mock_bus = MagicMock()
    mock_bus.client.set = AsyncMock(return_value=True)
    mock_bus.client.delete = AsyncMock(return_value=True)

    # Testa _handle_callback com parametro chat_id explicito
    text, keyboard, needs_back = await _handle_callback("cancelar", mock_bus, chat_id=12345)
    assert "Menu" in text or "Atalhos" in text
    assert keyboard is not None
    assert needs_back is True


@pytest.mark.asyncio
async def test_extra_coverage_handle_commands() -> None:
    mock_bus = MagicMock()
    mock_bus.client.set = AsyncMock(return_value=True)
    mock_bus.client.delete = AsyncMock(return_value=True)

    # Testa /cancelar
    text, kb = await _handle_command("/cancelar", mock_bus, chat_id=12345, _user_name="Gustavo")
    assert "cancelada" in text
    assert kb is not None

    # Testa /lgpd
    text, kb = await _handle_command("/lgpd", mock_bus, chat_id=12345, _user_name="Gustavo")
    assert "LGPD" in text or "DPO" in text
    assert kb is not None
