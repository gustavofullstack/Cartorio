"""Testes para app/integrations/opencode_generic.py (provider OpenAI-compat).

Cobre:
1. ProviderConfig.is_configured
2. chat() -> CONFIG quando provider nao configurado
3. chat() -> LGPD_BLOCKED sem consentimento
4. chat() -> CONFIG quando messages vazio
5. PROVIDER_DISPATCH (tabela dispatch)

Sobe cobertura opencode_generic.py de 0% -> >=60%.
"""

from __future__ import annotations

import asyncio

import pytest

from app.integrations.opencode_generic import (
    PROVIDER_DISPATCH,
    ProviderConfig,
    chat,
)
from app.integrations.opencode_go import ChatErrorKind


def test_provider_config_is_configured_todos_campos_preenchidos() -> None:
    """Provider configurado tem todos os campos nao-vazios."""
    cfg = ProviderConfig(
        name="opencode_free_1",
        base_url="https://api.opencode.ai/v1",
        api_key="sk-test",
        model="minimax-m3",
    )
    assert cfg.is_configured() is True


def test_provider_config_is_configured_sem_api_key() -> None:
    """Provider sem api_key NAO esta configurado."""
    cfg = ProviderConfig(
        name="opencode_free_1",
        base_url="https://api.opencode.ai/v1",
        api_key="",
        model="minimax-m3",
    )
    assert cfg.is_configured() is False


def test_provider_config_is_configured_sem_model() -> None:
    """Provider sem model NAO esta configurado."""
    cfg = ProviderConfig(
        name="opencode_free_1",
        base_url="https://api.opencode.ai/v1",
        api_key="sk-test",
        model="",
    )
    assert cfg.is_configured() is False


def test_provider_config_is_configured_sem_base_url() -> None:
    """Provider sem base_url NAO esta configurado."""
    cfg = ProviderConfig(
        name="opencode_free_1",
        base_url="",
        api_key="sk-test",
        model="minimax-m3",
    )
    assert cfg.is_configured() is False


def test_provider_config_timeout_default_30s() -> None:
    """Default timeout eh 30s."""
    cfg = ProviderConfig(
        name="p",
        base_url="https://x",
        api_key="y",
        model="z",
    )
    assert cfg.timeout_seconds == 30.0


def test_provider_dispatch_tem_14_providers() -> None:
    """Tabela PROVIDER_DISPATCH tem 14 providers (Sprint 47 + Zen accounts)."""
    assert len(PROVIDER_DISPATCH) == 14
    # Alguns providers canonicos devem estar presentes
    assert "opencode_go" in PROVIDER_DISPATCH
    assert "jules" in PROVIDER_DISPATCH
    assert "openclaw" in PROVIDER_DISPATCH
    assert "litellm" in PROVIDER_DISPATCH  # Turno 47
    assert "opencode_zen_account_1" in PROVIDER_DISPATCH
    assert "opencode_zen_account_2" in PROVIDER_DISPATCH
    assert "opencode_zen_account_3" in PROVIDER_DISPATCH


def test_chat_levanta_CONFIG_quando_provider_nao_configurado() -> None:
    """Provider com api_key vazia -> ChatError CONFIG."""
    cfg = ProviderConfig(
        name="empty_provider",
        base_url="https://x",
        api_key="",
        model="m",
    )

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat([{"role": "user", "content": "oi"}], config=cfg, consent_granted=True)
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.CONFIG

    asyncio.run(_run())


def test_chat_levanta_LGPD_BLOCKED_sem_consentimento() -> None:
    """Sem consentimento -> ChatError LGPD_BLOCKED."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://x",
        api_key="k",
        model="m",
    )

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=cfg,
                consent_granted=False,  # SEM consentimento
            )
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED

    asyncio.run(_run())


def test_chat_levanta_CONFIG_com_messages_vazio() -> None:
    """Messages vazio -> ChatError CONFIG."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://x",
        api_key="k",
        model="m",
    )

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat([], config=cfg, consent_granted=True)
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.CONFIG

    asyncio.run(_run())


def test_chat_levanta_HTTP_4xx_em_response_erro() -> None:
    """Response HTTP >= 400 -> ChatError HTTP_4XX/5XX."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
        timeout_seconds=5.0,
    )

    class FakeResp:
        status_code = 401
        text = "Unauthorized"

        def json(self) -> dict:
            return {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    async def _run() -> None:

        with pytest.raises(Exception) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=cfg,
                consent_granted=True,
            )
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.HTTP_4XX
        assert exc_info.value.status_code == 401

    # Patch httpx.AsyncClient via abordagem alternativa: patch httpx.AsyncClient
    # diretamente no module. Como test usa async, fazemos via asyncio.run + patch
    import unittest.mock as mock

    with mock.patch("httpx.AsyncClient", FakeClient):
        asyncio.run(_run())


def test_chat_levanta_HTTP_5xx_em_response_500() -> None:
    """Response HTTP 500 -> ChatError HTTP_5XX."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
        timeout_seconds=5.0,
    )

    class FakeResp:
        status_code = 500
        text = "Internal Server Error"

        def json(self) -> dict:
            return {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=cfg,
                consent_granted=True,
            )
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.HTTP_5XX

    import unittest.mock as mock

    with mock.patch("httpx.AsyncClient", FakeClient):
        asyncio.run(_run())
