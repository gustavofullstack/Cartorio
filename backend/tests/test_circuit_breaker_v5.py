"""Testes unitários para o Circuit Breaker Redis-based do fallback de LLM (Wave 5 S5.T4).

Valida:
- _is_circuit_open retorna False se Redis offline (fail-open)
- _record_failure incrementa e abre circuito ao atingir threshold
- _record_success reseta falhas e fecha circuito

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.fallback import (
    _is_circuit_open,
    _record_failure,
    _record_success,
)

# As funções CB fazem lazy import: `from app.services.redis_bus import get_bus`
# Portanto, o patch deve ser no módulo de origem com create=True,
# já que o import acontece dentro da chamada da função.
PATCH_TARGET = "app.services.redis_bus.get_bus"


@pytest.mark.asyncio
async def test_circuit_breaker_fail_open_when_redis_down() -> None:
    """Se Redis estiver offline, _is_circuit_open retorna False (fail-open)."""
    with patch(PATCH_TARGET, side_effect=Exception("Connection refused")):
        result = await _is_circuit_open("opencode_go")
        assert result is False


@pytest.mark.asyncio
async def test_circuit_breaker_closed_by_default() -> None:
    """Se não houver chave cb:open no Redis, circuito está fechado."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        result = await _is_circuit_open("opencode_go")
        assert result is False
        mock_client.get.assert_called_once_with("cb:open:opencode_go")


@pytest.mark.asyncio
async def test_circuit_breaker_open_when_key_set() -> None:
    """Se chave cb:open:provider == '1', circuito está aberto."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=b"1")
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        result = await _is_circuit_open("opencode_go")
        assert result is True


@pytest.mark.asyncio
async def test_record_failure_opens_circuit_at_threshold() -> None:
    """Após 3 falhas consecutivas, o circuito deve abrir (setex cb:open)."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=3)
    mock_client.expire = AsyncMock()
    mock_client.setex = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        await _record_failure("test_provider", threshold=3, open_time_seconds=300)
        mock_client.setex.assert_called_once_with("cb:open:test_provider", 300, "1")
        mock_client.delete.assert_called_once_with("cb:fail:test_provider")


@pytest.mark.asyncio
async def test_record_failure_below_threshold_no_open() -> None:
    """Com menos de 3 falhas, o circuito permanece fechado."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=2)
    mock_client.expire = AsyncMock()
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        await _record_failure("test_provider", threshold=3)
        mock_client.setex.assert_not_called()


@pytest.mark.asyncio
async def test_record_success_resets_circuit() -> None:
    """Após sucesso, as chaves de falha e abertura devem ser deletadas."""
    mock_client = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        await _record_success("test_provider")
        assert mock_client.delete.call_count == 2
        mock_client.delete.assert_any_call("cb:fail:test_provider")
        mock_client.delete.assert_any_call("cb:open:test_provider")


@pytest.mark.asyncio
async def test_record_failure_silent_on_redis_down() -> None:
    """Se Redis estiver offline, _record_failure não levanta exceção."""
    with patch(PATCH_TARGET, side_effect=Exception("offline")):
        await _record_failure("test_provider")  # Não deve levantar


@pytest.mark.asyncio
async def test_record_success_silent_on_redis_down() -> None:
    """Se Redis estiver offline, _record_success não levanta exceção."""
    with patch(PATCH_TARGET, side_effect=Exception("offline")):
        await _record_success("test_provider")  # Não deve levantar


@pytest.mark.asyncio
async def test_record_failure_default_5_attempts_opens_5_hours() -> None:
    """P0 Gustavo: Padrão do _record_failure exige 5 falhas e 18000s (5h) de circuito aberto."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=5)
    mock_client.expire = AsyncMock()
    mock_client.setex = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_bus = MagicMock()
    mock_bus.client = mock_client

    with patch(PATCH_TARGET, return_value=mock_bus):
        await _record_failure("MiniMax_direct")
        mock_client.setex.assert_called_once_with("cb:open:MiniMax_direct", 18000, "1")
        mock_client.delete.assert_called_once_with("cb:fail:MiniMax_direct")

