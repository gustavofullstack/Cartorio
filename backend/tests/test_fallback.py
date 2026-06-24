"""Testes para fallback LLM (placeholder LiteLLM).

BLOCKER 6 da auditoria LGPD 2026-06-23:
- Status atual: Implementado
- Em sprint 2: implementar openclaw.py com mesma assinatura + scrubbing
- chat_with_fallback tenta opencode_go e em caso de falha tenta openclaw.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.integrations.opencode_go import ChatError, ChatErrorKind


@pytest.mark.asyncio
async def test_chat_with_fallback_delegates_to_opencode_go():
    """chat_with_fallback delega ao opencode_go por enquanto."""
    from app.integrations.fallback import chat_with_fallback

    with patch("app.integrations.opencode_go.chat_with_settings") as mock_opencode:
        mock_opencode.return_value = MagicMock(content="ok_opencode")

        result = await chat_with_fallback(
            messages=[{"role": "user", "content": "Ola"}],
            consent_granted=True,
            actor_id="cliente:test",
        )

    assert result.content == "ok_opencode"
    mock_opencode.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_openclaw_on_failure():
    """chat_with_fallback tenta openclaw se opencode_go falhar com timeout, 5xx, etc."""
    from app.integrations.fallback import chat_with_fallback

    with patch("app.integrations.opencode_go.chat_with_settings") as mock_opencode, \
         patch("app.integrations.openclaw.chat_with_settings") as mock_openclaw:

        # Configura opencode_go para falhar com TIMEOUT
        mock_opencode.side_effect = ChatError("timeout", kind=ChatErrorKind.TIMEOUT)

        # Configura openclaw para ter sucesso
        mock_openclaw.return_value = MagicMock(content="ok_openclaw")

        result = await chat_with_fallback(
            messages=[{"role": "user", "content": "Ola"}],
            consent_granted=True,
            actor_id="cliente:test",
        )

    assert result.content == "ok_openclaw"
    mock_opencode.assert_called_once()
    mock_openclaw.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_does_not_fallback_on_lgpd_blocked():
    """chat_with_fallback NAO deve tentar fallback se erro for de negocio (ex LGPD)."""
    from app.integrations.fallback import chat_with_fallback

    with patch("app.integrations.opencode_go.chat_with_settings") as mock_opencode, \
         patch("app.integrations.openclaw.chat_with_settings") as mock_openclaw:

        # Configura opencode_go para falhar com LGPD_BLOCKED
        mock_opencode.side_effect = ChatError("blocked", kind=ChatErrorKind.LGPD_BLOCKED)

        with pytest.raises(ChatError) as exc_info:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "Ola"}],
                consent_granted=False,
                actor_id="cliente:test",
            )

        assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED

    mock_opencode.assert_called_once()
    mock_openclaw.assert_not_called()

@pytest.mark.asyncio
async def test_chat_with_fallback_raises_if_both_fail():
    """chat_with_fallback levanta ChatError do openclaw se ambos falharem."""
    from app.integrations.fallback import chat_with_fallback
    import app.integrations.openclaw as openclaw

    with patch("app.integrations.opencode_go.chat_with_settings") as mock_opencode, \
         patch("app.integrations.openclaw.chat_with_settings") as mock_openclaw:

        mock_opencode.side_effect = ChatError("timeout", kind=ChatErrorKind.TIMEOUT)
        mock_openclaw.side_effect = openclaw.ChatError("timeout2", kind=ChatErrorKind.TIMEOUT)

        with pytest.raises(ChatError) as exc_info:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "Ola"}],
                consent_granted=True,
                actor_id="cliente:test",
            )

        assert "Fallback also failed:" in exc_info.value.args[0]
        assert exc_info.value.kind == ChatErrorKind.TIMEOUT
