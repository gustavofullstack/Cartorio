"""Testes para fallback LLM (Opencode-Go -> OpenClaw)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse
from app.integrations.fallback import chat_with_fallback


@pytest.mark.asyncio
async def test_chat_with_fallback_success_primary():
    """Se o primario funcionar, retorna a resposta sem chamar o fallback."""
    mock_resp = ChatResponse(
        content="Ola primario",
        model="minimax-m3",
        tokens_in=10,
        tokens_out=15,
        latency_ms=100,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
        )

        assert res.content == "Ola primario"
        mock_primary.assert_called_once()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_triggers_fallback_on_rate_limit():
    """Se o primario retornar rate limit, executa o fallback com sucesso."""
    mock_resp = ChatResponse(
        content="Ola fallback",
        model="openclaw",
        tokens_in=10,
        tokens_out=15,
        latency_ms=100,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("Rate limit", kind=ChatErrorKind.RATE_LIMITED)
        mock_fallback.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
        )

        assert res.content == "Ola fallback"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_no_fallback_on_consent_blocked():
    """Se o primario falhar com LGPD_BLOCKED, nao executa o fallback."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("LGPD Blocked", kind=ChatErrorKind.LGPD_BLOCKED)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=False,
            )

        assert exc.value.kind == ChatErrorKind.LGPD_BLOCKED
        mock_primary.assert_called_once()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_raises_if_both_fail():
    """Se ambos os provedores falharem, propaga a excecao."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("Network primary", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = ChatError("Network fallback", kind=ChatErrorKind.NETWORK)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=True,
            )

        assert "Network fallback" in str(exc.value)
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()
