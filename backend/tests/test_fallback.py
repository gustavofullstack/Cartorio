"""Testes para fallback LLM (placeholder LiteLLM).

BLOCKER 6 da auditoria LGPD 2026-06-23:
- Status atual: PLACEHOLDER
- Em sprint 2: implementar openclaw.py com mesma assinatura + scrubbing
- Por enquanto, chat_with_fallback delega direto ao opencode_go
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_chat_with_fallback_delegates_to_opencode_go():
    """chat_with_fallback delega ao opencode_go por enquanto (placeholder)."""
    from app.integrations.fallback import chat_with_fallback

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat_with_fallback(
            messages=[{"role": "user", "content": "Ola"}],
            consent_granted=True,
            actor_id="cliente:test",
        )

    assert result.content == "ok"


@pytest.mark.asyncio
async def test_chat_with_fallback_propagates_consent_and_actor():
    """chat_with_fallback passa consent + actor_id para opencode_go."""
    from app.integrations.fallback import chat_with_fallback

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        # Sem consentimento - deve bloquear
        from app.integrations.opencode_go import ChatError

        with pytest.raises(ChatError):
            await chat_with_fallback(
                messages=[{"role": "user", "content": "Ola"}],
                consent_granted=False,
                actor_id="cliente:test",
            )


@pytest.mark.asyncio
async def test_fallback_module_docstring_documents_status():
    """Modulo fallback documenta que eh PLACEHOLDER (LGPD audita isso)."""
    from app.integrations import fallback

    docstring = fallback.__doc__ or ""
    assert "PLACEHOLDER" in docstring.upper()
    assert "LiteLLM" in docstring or "openclaw" in docstring.lower()
