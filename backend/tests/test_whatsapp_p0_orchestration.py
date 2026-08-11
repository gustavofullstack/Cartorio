"""P0 WhatsApp orchestration — TDD da auditoria Pietra 2026-08-11.

Cobre: stale expiry, FIFO/lock, idempotencia de saida, burst sem perda,
TTL 24h. Sem Redis real (mocks). Nao toca producao.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.whatsapp_orchestration import (
    IDEMPOTENCY_TTL_SEC,
    STALE_MAX_AGE_SEC,
    acquire_conversation_lock,
    check_output_idempotency,
    is_stale_event,
    number_burst_messages,
    release_conversation_lock,
)


def test_stale_event_expires_after_max_age() -> None:
    now = 1_000_000.0
    assert is_stale_event(now - STALE_MAX_AGE_SEC - 1, now=now) is True
    assert is_stale_event(now - 10, now=now) is False


def test_52_minute_delay_is_stale() -> None:
    now = 1_000_000.0
    assert is_stale_event(now - (52 * 60 + 10), now=now) is True


def test_number_burst_keeps_all_messages_in_order() -> None:
    texts = [
        "quem e voce",
        "reconhecimento de firma",
        "PDF no celular",
        "tres firmas e quatro paginas",
        "apartamento 420 mil",
        "procuracao no hospital",
        "ata notarial",
        "testamento",
        "protocolo TESTE-2026-000123",
        "direitos LGPD",
    ]
    block = number_burst_messages(texts)
    assert "10 mensagens" in block
    for i, t in enumerate(texts, start=1):
        assert f"{i})" in block
        assert t in block
    assert block.index("quem e voce") < block.index("testamento")
    assert block.index("testamento") < block.index("direitos LGPD")


def test_number_burst_single_passthrough() -> None:
    assert number_burst_messages(["Oi"]) == "Oi"


def test_number_burst_two_messages_does_not_drop_first() -> None:
    block = number_burst_messages(["Oi", "Quanto custa autenticacao?"])
    assert "Oi" in block
    assert "Quanto custa autenticacao?" in block


def test_idempotency_ttl_is_24h() -> None:
    assert IDEMPOTENCY_TTL_SEC == 86400


@pytest.mark.asyncio
async def test_conversation_lock_is_exclusive() -> None:
    bus = MagicMock()
    bus.client.set = AsyncMock(side_effect=[True, None])
    bus.client.delete = AsyncMock(return_value=1)
    with patch("app.services.whatsapp_orchestration.get_bus", return_value=bus):
        first = await acquire_conversation_lock("whatsapp", "jid-a")
        second = await acquire_conversation_lock("whatsapp", "jid-a")
        assert first is True
        assert second is False
        await release_conversation_lock("whatsapp", "jid-a")
    bus.client.delete.assert_awaited()


@pytest.mark.asyncio
async def test_output_idempotency_blocks_duplicate_send() -> None:
    bus = MagicMock()
    bus.client.set = AsyncMock(side_effect=[True, None])
    with patch("app.services.whatsapp_orchestration.get_bus", return_value=bus):
        first = await check_output_idempotency("whatsapp", "jid-a", "hash-1")
        second = await check_output_idempotency("whatsapp", "jid-a", "hash-1")
    assert first is False  # False = pode enviar
    assert second is True  # True = ja enviado, pular
