"""Testes para app/integrations/opencode_generic.py (SQUAD C cobertura).

Cobre:
1. ProviderConfig e is_configured
2. get_config_for para todos os providers OpenAI-compat
3. chat function: happy path com mock, timeouts, status erros, PII scrubbing (input/output)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.opencode_generic import ProviderConfig, chat, get_config_for
from app.integrations.opencode_go import ChatError, ChatErrorKind


def test_provider_config_is_configured() -> None:
    """is_configured retorna True apenas se todos os campos obrigatorios estao preenchidos."""
    c1 = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")
    assert c1.is_configured() is True

    c2 = ProviderConfig(name="test", base_url="", api_key="key", model="model")
    assert c2.is_configured() is False

    c3 = ProviderConfig(name="test", base_url="http://test.com", api_key=None, model="model")
    assert c3.is_configured() is False

    c4 = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="")
    assert c4.is_configured() is False


def test_get_config_for_all_providers() -> None:
    """get_config_for mapeia corretamente os nomes dos provedores."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.opencode_go_base_url = "http://opencode_go"
        mock_settings.opencode_go_api_key = "key_go"
        mock_settings.opencode_go_model = "model_go"

        mock_settings.opencode_free_1_base_url = "http://free1"
        mock_settings.opencode_free_1_api_key = "key1"
        mock_settings.opencode_free_1_model = "model1"

        mock_settings.opencode_free_2_base_url = "http://free2"
        mock_settings.opencode_free_2_api_key = "key2"
        mock_settings.opencode_free_2_model = "model2"

        mock_settings.opencode_free_3_base_url = "http://free3"
        mock_settings.opencode_free_3_api_key = "key3"
        mock_settings.opencode_free_3_model = "model3"

        mock_settings.openrouter_base_url = "http://router"
        mock_settings.openrouter_api_key = "key_router"
        mock_settings.openrouter_model = "model_router"

        mock_settings.groq_base_url = "http://groq"
        mock_settings.groq_api_key = "key_groq"
        mock_settings.groq_model = "model_groq"

        mock_settings.mistral_base_url = "http://mistral"
        mock_settings.mistral_api_key = "key_mistral"
        mock_settings.mistral_model = "model_mistral"

        mock_settings.google_ai_studio_base_url = "http://google"
        mock_settings.google_ai_studio_api_key = "key_google"
        mock_settings.google_ai_studio_model = "model_google"

        mock_settings.litellm_base_url = "http://litellm"
        mock_settings.litellm_api_key = "key_litellm"
        mock_settings.litellm_model = "model_litellm"

        providers = [
            "opencode_go",
            "opencode_free_1",
            "opencode_free_2",
            "opencode_free_3",
            "openrouter",
            "groq",
            "mistral",
            "google_ai_studio",
            "litellm",
        ]
        for p in providers:
            cfg = get_config_for(p)
            assert cfg is not None
            assert cfg.name == p

        assert get_config_for("invalid_provider") is None


@pytest.mark.asyncio
async def test_chat_raises_config_error_when_not_configured() -> None:
    """chat levanta ChatError se o provedor nao estiver configurado."""
    cfg = ProviderConfig(name="test", base_url="", api_key="key", model="model")
    with pytest.raises(ChatError) as exc_info:
        await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
    assert exc_info.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_raises_lgpd_blocked_without_consent() -> None:
    """chat levanta ChatError se consentimento LGPD nao for concedido."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")
    with pytest.raises(ChatError) as exc_info:
        await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=False)
    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_chat_raises_config_error_with_empty_messages() -> None:
    """chat levanta ChatError se lista de mensagens for vazia."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")
    with pytest.raises(ChatError) as exc_info:
        await chat([], config=cfg, consent_granted=True)
    assert exc_info.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_scrubs_pii_in_input_and_output() -> None:
    """chat mascara PII (como CPF) na entrada enviada e na saida recebida."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {"content": "O CPF mascarado do cliente e 123.456.789-09"},
                "finish_reason": "stop",
            }
        ],
        "model": "model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }

    # patch httpx AsyncClient post
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)) as mock_post:
        resp = await chat(
            [{"role": "user", "content": "Meu CPF e 987.654.321-00"}],
            config=cfg,
            consent_granted=True,
        )
        assert resp.pii_redacted_count >= 1
        assert resp.output_pii_redacted_count >= 1
        assert "987.654.321-00" not in mock_post.call_args[1]["json"]["messages"][0]["content"]
        assert "123.456.789-09" not in resp.content


@pytest.mark.asyncio
async def test_chat_handles_timeouts_and_http_errors() -> None:
    """chat trata timeouts e erros de rede do httpx."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.TimeoutException("boom"))):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.TIMEOUT

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.HTTPError("net error"))):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.NETWORK


@pytest.mark.asyncio
async def test_chat_handles_non_200_status_codes() -> None:
    """chat trata HTTP 4XX e 5XX do upstream de forma adequada."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request Details"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.HTTP_4XX

    mock_resp.status_code = 502
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.HTTP_5XX


@pytest.mark.asyncio
async def test_chat_handles_malformed_json_and_unexpected_structure() -> None:
    """chat trata respostas que nao sao JSON valido ou com estrutura inesperada."""
    cfg = ProviderConfig(name="test", base_url="http://test.com", api_key="key", model="model")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("not json")

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.PARSE

    mock_resp.json.side_effect = None
    mock_resp.json.return_value = {"unexpected": "payload"}
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat([{"role": "user", "content": "hello"}], config=cfg, consent_granted=True)
        assert exc_info.value.kind == ChatErrorKind.PARSE
