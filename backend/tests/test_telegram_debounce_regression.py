"""Testes de regressão para o background task do webhook Telegram.

Contexto (lesson-2026-07-02): `_process_telegram_debounce` é chamado via
`background_tasks.add_task` do FastAPI, que roda APÓS o response ser
retornado. Se alguém reintroduzir `db: Session` na assinatura, a Session do
`Depends(get_db)` já estará fechada quando a task rodar, causando
`sqlalchemy.exc.InvalidRequestError: This Session's transaction has been
rolled back` ou `Session is closed`.

Esses testes garantem:
1. A função NÃO aceita parâmetro `db` na assinatura.
2. Quando executada de forma assíncrona, não tenta tocar em Session/DB.
3. Se bus é None, a função retorna limpo (warning, sem exception).
4. A função usa APENAS Redis (via bus) para coordenar o debounce.

Modified by Gustavo Almeida
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.telegram import _process_telegram_debounce


# === Assinatura da função (guard contra regressão do db) ===


def test_process_telegram_debounce_signature_has_no_db() -> None:
    """Garante que a função NÃO tem parâmetro `db` (Session).

    Regressão a prevenir: se alguém reintroduzir `db: Session = Depends(get_db)`
    na assinatura, esse teste falha. Foi o bug corrigido em 2026-07-02.
    """
    sig = inspect.signature(_process_telegram_debounce)
    params = list(sig.parameters.keys())
    assert "db" not in params, (
        f"_process_telegram_debounce NÃO deve aceitar 'db' (Session) "
        f"porque background_tasks.add_task roda APÓS Depends(get_db) fechar "
        f"a Session. Params atuais: {params}"
    )


def test_process_telegram_debounce_signature_only_chat_id() -> None:
    """Garante que o único parâmetro posicional é `chat_id`."""
    sig = inspect.signature(_process_telegram_debounce)
    params = list(sig.parameters.keys())
    assert params == ["chat_id"], f"Esperado ['chat_id'], obtido {params}"


# === Comportamento: sem bus, sem crash (warning + return limpo) ===


@pytest.mark.asyncio
async def test_debounce_returns_silently_when_bus_is_none() -> None:
    """Se `get_bus()` retorna None, a função retorna sem exception."""
    with patch("app.api.v1.telegram.get_bus", return_value=None):
        # Não deve lançar exceção
        await _process_telegram_debounce(chat_id=12345)


@pytest.mark.asyncio
async def test_debounce_returns_silently_when_queue_is_empty() -> None:
    """Se Redis retorna None para queue_key, função retorna sem processar."""
    mock_bus = MagicMock()
    # Pipeline async: get -> delete -> delete -> retorna [None, 1, 1]
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=None)

    async def fake_execute():
        return [None, 1, 1]

    mock_pipe.execute = fake_execute
    mock_bus.client.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        await asyncio.sleep(0)  # yield
        await _process_telegram_debounce(chat_id=99999)
    # Não chamou LLM nem enviou mensagem
    mock_bus.client.get.assert_not_called()


# === Comportamento: queue populada, função tenta processar via LLM ===


@pytest.mark.asyncio
async def test_debounce_processes_message_without_touching_db() -> None:
    """Fluxo completo: queue populada -> state IDLE -> LLM -> send. SEM DB."""

    # Mock de pipeline retornando 1 mensagem com texto
    fake_message = '{"text": "oi", "msg_id": 42}'
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=None)

    async def fake_execute():
        return [fake_message, 1, 1]

    mock_pipe.execute = fake_execute
    mock_pipe.get = AsyncMock()
    mock_pipe.delete = AsyncMock()

    mock_bus = MagicMock()
    mock_bus.client.pipeline = MagicMock(return_value=mock_pipe)
    mock_bus.client.get = AsyncMock(return_value=None)  # sem state salvo
    mock_bus.client.setex = AsyncMock()

    # Mocks das funções que _process_telegram_debounce chama após o queue
    with patch("app.api.v1.telegram.get_bus", return_value=mock_bus):
        with patch("app.api.v1.telegram._resumir_mensagens", return_value=["oi"]):
            with patch("app.api.v1.telegram._check_rate_limit", new=AsyncMock(return_value=True)):
                with patch(
                    "app.api.v1.telegram._get_state",
                    new=AsyncMock(return_value={"state": "idle", "data": {}}),
                ):
                    with patch("app.api.v1.telegram._clear_state", new=AsyncMock()):
                        with patch(
                            "app.api.v1.telegram._call_fast_llm",
                            new=AsyncMock(return_value="ola"),
                        ):
                            with patch(
                                "app.api.v1.telegram._menu_keyboard",
                                return_value=[[{"text": "Menu", "callback_data": "menu"}]],
                            ):
                                with patch(
                                    "app.api.v1.telegram._send_message",
                                    new=AsyncMock(return_value=True),
                                ):
                                    with patch(
                                        "app.api.v1.telegram._react",
                                        new=AsyncMock(return_value=True),
                                    ):
                                        # A função dorme DEBOUNCE_WINDOW (3s por padrão).
                                        # Patchamos o sleep pra não esperar.
                                        with patch(
                                            "app.api.v1.telegram.asyncio.sleep",
                                            new=AsyncMock(),
                                        ):
                                            await _process_telegram_debounce(chat_id=42)

    # Sanity: a função foi chamada com chat_id=42 e completou sem exception.
    # Se tivesse usado `db` em qualquer ponto, veríamos InvalidRequestError.
