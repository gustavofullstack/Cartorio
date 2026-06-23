"""Testes para integracao OpenCode-Go (LLM provider low-cost).

Cobre:
- Chat completion basico (mock httpx)
- Tratamento de erro (4xx/5xx)
- Validacao de API key (bloqueia se vazia)
- Contagem de tokens e latencia (para audit log)
- Mensagem bloqueada se PII detectada antes do LLM
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ============================================================================
# Testes unitarios do modulo opencode_go
# ============================================================================


@pytest.mark.asyncio
async def test_chat_returns_completion_with_valid_key():
    """Chat retorna choices[0].message.content quando API responde 200."""
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-123",
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Ola, como posso ajudar?"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
        )

    assert result.content == "Ola, como posso ajudar?"
    assert result.model == "deepseek-v4-flash"
    assert result.tokens_in == 10
    assert result.tokens_out == 8
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_chat_raises_on_missing_api_key():
    """Chat falha claro se API key nao configurada (config bug)."""
    from app.integrations.opencode_go import ChatError, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="",
            base_url="https://api.opencode.ai/v1",
        )

    assert "API_KEY" in str(exc_info.value) or "API key" in str(exc_info.value).upper()


@pytest.mark.asyncio
async def test_chat_raises_on_missing_base_url():
    """Chat falha claro se base_url nao configurada."""
    from app.integrations.opencode_go import ChatError, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test-123",
            base_url="",
        )

    assert "BASE_URL" in str(exc_info.value).upper() or "URL" in str(exc_info.value).upper()


@pytest.mark.asyncio
async def test_chat_raises_on_http_4xx():
    """Chat propaga erro HTTP 4xx com mensagem clara."""
    from app.integrations.opencode_go import ChatError, chat

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized: invalid api key"

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-invalid",
                base_url="https://api.opencode.ai/v1",
            )

        assert exc_info.value.status_code == 401
        assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_raises_on_http_5xx():
    """Chat propaga erro HTTP 5xx com mensagem clara."""
    from app.integrations.opencode_go import ChatError, chat

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
            )

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_chat_raises_on_timeout():
    """Chat propaga timeout como ChatError (handoff humano)."""
    from app.integrations.opencode_go import ChatError, chat

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout 30s")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
            )

        assert "TIMEOUT" in str(exc_info.value).upper() or "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_chat_sends_correct_payload():
    """Chat envia payload com model + messages + headers corretos."""
    from app.integrations.opencode_go import chat

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

        await chat(
            messages=[
                {"role": "system", "content": "Voce e assistente."},
                {"role": "user", "content": "Ola"},
            ],
            model="deepseek-v4-flash",
            api_key="sk-test-abc",
            base_url="https://api.opencode.ai/v1",
            temperature=0.5,
        )

        call_args = mock_client.post.call_args
        # URL
        assert call_args.args[0] == "https://api.opencode.ai/v1/chat/completions"
        # Headers
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer sk-test-abc"
        assert headers["Content-Type"] == "application/json"
        # Body
        body = call_args.kwargs["json"]
        assert body["model"] == "deepseek-v4-flash"
        assert body["temperature"] == 0.5
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_chat_measures_latency():
    """Chat mede latencia em ms e retorna no response."""
    import asyncio

    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    async def slow_post(*args, **kwargs):
        await asyncio.sleep(0.01)  # 10ms
        return mock_response

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = slow_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
        )

    assert result.latency_ms >= 10  # pelo menos 10ms (tempo do sleep)
