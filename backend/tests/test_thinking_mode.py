"""T57 E08 — testes do thinking mode (Literal disabled/enabled/adaptive).

Cobre:
1. config.py expoe `llm_thinking_mode` e `opencode_go_thinking_mode` como Literal.
2. Default `llm_thinking_mode = "adaptive"` (recomendado p/ 1M ctx DeepSeek/MiniMax).
3. Default `opencode_go_thinking_mode = "disabled"` (compat com codigo legado).
4. chat() injeta `thinking` no payload quando mode != "disabled".
5. chat() NAO injeta `thinking` quando mode == "disabled".
6. chat_with_settings() le `settings.opencode_go_thinking_mode`.
7. Modo invalido (string fora do Literal) falha na validacao do Pydantic.

Mock httpx.AsyncClient — nao chama API real.
Modified by Gustavo Almeida — 2026-07-01 (turno 53, T57 E08)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# config.py — campos e defaults
# ============================================================================


def test_llm_thinking_mode_default_is_adaptive():
    """Default global: adaptive (provider decide, otimiza tokens)."""
    from app.config import Settings

    s = Settings()
    assert s.llm_thinking_mode == "adaptive"


def test_opencode_go_thinking_mode_default_is_adaptive():
    """Default do provider: adaptive (consistente com llm_thinking_mode global)."""
    from app.config import Settings

    # Cria Settings sem ler .env (so defaults do codigo)
    s = Settings(_env_file=None)
    assert s.opencode_go_thinking_mode == "adaptive"


def test_opencode_go_thinking_mode_accepts_valid_literal():
    """Aceita os 3 valores do Literal."""
    from app.config import Settings

    for mode in ("disabled", "enabled", "adaptive"):
        s = Settings(_env_file=None, opencode_go_thinking_mode=mode)
        assert s.opencode_go_thinking_mode == mode


def test_opencode_go_thinking_mode_rejects_invalid_value():
    """Valor fora do Literal falha validacao Pydantic."""
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, opencode_go_thinking_mode="always")  # type: ignore[arg-type]


def test_llm_thinking_mode_rejects_invalid_value():
    """Valor fora do Literal falha validacao Pydantic."""
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_thinking_mode="turbo")  # type: ignore[arg-type]


# ============================================================================
# opencode_go.py — injecao de `thinking` no payload
# ============================================================================


def _mock_llm_response() -> MagicMock:
    """Mock de response 200 do provider."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-thinking-test",
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Resposta teste"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }
    return mock_response


def _capture_post_payload(mock_client_cls: MagicMock) -> dict:
    """Helper: captura o payload enviado em mock_client.post()."""
    call_args = mock_client_cls.return_value.post.call_args
    # post(url, json=payload, headers=...)
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert payload is not None, f"post() chamado sem json: {call_args}"
    return payload


@pytest.mark.asyncio
async def test_chat_disabled_mode_does_not_inject_thinking():
    """thinking_mode='disabled' NAO envia campo thinking no payload."""
    from app.integrations.opencode_go import chat

    mock_response = _mock_llm_response()
    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Oi"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            thinking_mode="disabled",
        )

    payload = _capture_post_payload(mock_client_cls)
    assert "thinking" not in payload, f"thinking NAO deveria estar no payload: {payload}"


@pytest.mark.asyncio
async def test_chat_enabled_mode_injects_thinking_enabled():
    """thinking_mode='enabled' envia thinking={'type': 'enabled'}."""
    from app.integrations.opencode_go import chat

    mock_response = _mock_llm_response()
    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Oi"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            thinking_mode="enabled",
        )

    payload = _capture_post_payload(mock_client_cls)
    assert payload.get("thinking") == {"type": "enabled"}, f"thinking errado: {payload}"


@pytest.mark.asyncio
async def test_chat_adaptive_mode_injects_thinking_adaptive():
    """thinking_mode='adaptive' envia thinking={'type': 'adaptive'} (provider decide)."""
    from app.integrations.opencode_go import chat

    mock_response = _mock_llm_response()
    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Oi"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            thinking_mode="adaptive",
        )

    payload = _capture_post_payload(mock_client_cls)
    assert payload.get("thinking") == {"type": "adaptive"}, f"thinking errado: {payload}"


@pytest.mark.asyncio
async def test_chat_default_is_disabled():
    """Default do param thinking_mode eh 'disabled' (compat com codigo sem thinking)."""
    from app.integrations.opencode_go import chat

    mock_response = _mock_llm_response()
    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Oi"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            # thinking_mode NAO passado -> default
        )

    payload = _capture_post_payload(mock_client_cls)
    assert "thinking" not in payload, "default deveria ser disabled (sem thinking)"


# ============================================================================
# chat_with_settings — le settings.opencode_go_thinking_mode
# ============================================================================


@pytest.mark.asyncio
async def test_chat_with_settings_reads_thinking_mode_from_settings():
    """chat_with_settings() propaga settings.opencode_go_thinking_mode para chat()."""
    from app.config import settings
    from app.integrations.opencode_go import chat_with_settings

    # Força mode=adaptive via monkeypatch do settings (sem reload).
    original_mode = settings.opencode_go_thinking_mode
    settings.opencode_go_thinking_mode = "adaptive"
    try:
        mock_response = _mock_llm_response()
        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            await chat_with_settings(
                messages=[{"role": "user", "content": "Oi"}],
                consent_granted=True,
            )

        payload = _capture_post_payload(mock_client_cls)
        assert payload.get("thinking") == {"type": "adaptive"}
    finally:
        settings.opencode_go_thinking_mode = original_mode


@pytest.mark.asyncio
async def test_chat_with_settings_disabled_does_not_inject():
    """Quando settings esta em 'disabled', chat_with_settings NAO injeta thinking."""
    from app.config import settings
    from app.integrations.opencode_go import chat_with_settings

    original_mode = settings.opencode_go_thinking_mode
    settings.opencode_go_thinking_mode = "disabled"
    try:
        mock_response = _mock_llm_response()
        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            await chat_with_settings(
                messages=[{"role": "user", "content": "Oi"}],
                consent_granted=True,
            )

        payload = _capture_post_payload(mock_client_cls)
        assert "thinking" not in payload
    finally:
        settings.opencode_go_thinking_mode = original_mode