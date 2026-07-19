"""Contrato do provider ``cache`` como fallback deterministico e LGPD-safe."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.fallback import (
    CACHE_FALLBACK_RESPONSE,
    CACHE_PROVIDER,
    _call_provider,
    chat_with_fallback,
)
from app.integrations.opencode_go import ChatError, ChatErrorKind


@pytest.mark.asyncio
async def test_cache_provider_returns_static_response_without_using_messages() -> None:
    """O provider local não encaminha nem persiste o conteúdo da requisição."""
    messages = [{"role": "user", "content": "CPF 123.456.789-09"}]

    response = await _call_provider(
        CACHE_PROVIDER,
        messages,
        model="ignored-model",
        temperature=0.2,
        consent_granted=True,
        actor_id="test-actor",
        db=None,
        session_id=None,
        rate_limit_per_minute=None,
        request_id="test-request",
        client_ip=None,
    )

    assert response.content == CACHE_FALLBACK_RESPONSE
    assert response.model == "cache-failsafe-v1"
    assert response.tokens_in == 0
    assert response.tokens_out == 0
    assert response.raw is None
    assert "123.456.789-09" not in response.content


@pytest.mark.asyncio
async def test_cache_provider_enforces_consent_when_called_directly() -> None:
    """A rota local não pode contornar o consent gate ao usar o dispatcher."""
    with pytest.raises(ChatError) as exc_info:
        await _call_provider(
            CACHE_PROVIDER,
            [{"role": "user", "content": "oi"}],
            model=None,
            temperature=0.2,
            consent_granted=False,
            actor_id="test-actor",
            db=None,
            session_id=None,
            rate_limit_per_minute=None,
            request_id=None,
            client_ip=None,
        )

    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_cache_provider_is_reachable_after_upstream_failures() -> None:
    """Falhas upstream não impedem o último fallback determinístico."""
    calls: list[str] = []

    async def fail_upstream(provider: str, *args: object, **kwargs: object):
        calls.append(provider)
        raise ChatError("upstream down", kind=ChatErrorKind.NETWORK)

    with (
        patch("app.integrations.fallback._call_provider", new=fail_upstream),
        patch("app.integrations.fallback._is_circuit_open", new=AsyncMock(return_value=False)),
        patch("app.integrations.fallback._record_failure", new=AsyncMock()),
    ):
        # Restore only the cache dispatch so the test exercises the real
        # deterministic branch after two failed upstream providers.
        original_call = _call_provider

        async def dispatch(provider: str, *args: object, **kwargs: object):
            if provider == CACHE_PROVIDER:
                return await original_call(provider, *args, **kwargs)
            return await fail_upstream(provider, *args, **kwargs)

        with patch("app.integrations.fallback._call_provider", new=dispatch):
            response = await chat_with_fallback(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=["opencode_go", "openclaw", CACHE_PROVIDER],
            )

    assert response.content == CACHE_FALLBACK_RESPONSE
    assert calls == ["opencode_go", "openclaw"]
