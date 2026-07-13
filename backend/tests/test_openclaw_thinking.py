import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_openclaw_thinking_mode_adaptive():
    from app.integrations.openclaw import chat

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "oi"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_c = AsyncMock()
        mock_c.__aenter__.return_value = mock_c
        mock_c.__aexit__.return_value = False
        mock_c.post.return_value = mock_resp
        mock_client_cls.return_value = mock_c

        await chat(
            [{"role": "user", "content": "oi"}],
            base_url="http://test",
            api_key="sk-test",
            consent_granted=True,
            thinking_mode="adaptive",
        )

        call_args = mock_c.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload.get("thinking") == {"type": "adaptive"}


@pytest.mark.asyncio
async def test_openclaw_thinking_mode_disabled_by_default():
    from app.integrations.openclaw import chat

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "oi"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_c = AsyncMock()
        mock_c.__aenter__.return_value = mock_c
        mock_c.__aexit__.return_value = False
        mock_c.post.return_value = mock_resp
        mock_client_cls.return_value = mock_c

        await chat(
            [{"role": "user", "content": "oi"}],
            base_url="http://test",
            api_key="sk-test",
            consent_granted=True,
        )

        call_args = mock_c.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "thinking" not in payload
