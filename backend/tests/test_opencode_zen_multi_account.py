"""Contratos do roteamento OpenCode Zen multi-account, sem credenciais reais."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.fallback import chat_with_fallback
from app.integrations.opencode_generic import ChatError, ChatErrorKind, ChatResponse, get_config_for


def test_default_chain_prioritizes_three_independent_zen_slots() -> None:
    """A ordem declarada tenta cada conta Zen antes de providers legados."""
    from app.config import Settings

    default_chain = Settings.model_fields["llm_fallback_chain"].default
    assert isinstance(default_chain, str)
    assert default_chain.split(",")[:3] == [
        "opencode_zen_account_1",
        "opencode_zen_account_2",
        "opencode_zen_account_3",
    ]


@pytest.mark.parametrize(
    ("provider", "slot"),
    [
        ("opencode_zen_account_1", "1"),
        ("opencode_zen_account_2", "2"),
        ("opencode_zen_account_3", "3"),
    ],
)
def test_zen_account_config_uses_its_own_secret_only_env_slot(provider: str, slot: str) -> None:
    """Cada provider lê apenas suas próprias variáveis de ambiente/settings."""
    with patch("app.config.settings") as mock_settings:
        setattr(
            mock_settings, f"opencode_zen_account_{slot}_base_url", f"https://zen-{slot}.test/v1"
        )
        setattr(mock_settings, f"opencode_zen_account_{slot}_api_key", f"test-secret-{slot}")
        setattr(mock_settings, f"opencode_zen_account_{slot}_model", f"free-model-{slot}")
        config = get_config_for(provider)

    assert config is not None
    assert config.name == provider
    assert config.base_url == f"https://zen-{slot}.test/v1"
    assert config.api_key == f"test-secret-{slot}"
    assert config.model == f"free-model-{slot}"


def test_zen_accounts_are_registered_as_openai_compatible_providers() -> None:
    """Os três slots podem ser usados pela mesma cadeia e pelo mesmo contrato HTTP."""
    from app.integrations.fallback import _OPENAI_COMPAT_PROVIDERS

    assert {
        "opencode_zen_account_1",
        "opencode_zen_account_2",
        "opencode_zen_account_3",
    }.issubset(_OPENAI_COMPAT_PROVIDERS)


@pytest.mark.asyncio
async def test_unconfigured_zen_slot_skips_to_next_slot_without_opening_circuit() -> None:
    """Conta ausente não derruba a cadeia nem é tratada como falha de upstream."""
    calls: list[str] = []
    response = ChatResponse(
        content="resposta segura",
        model="free-model-2",
        tokens_in=1,
        tokens_out=1,
        latency_ms=1,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
        raw=None,
    )

    async def call_provider(provider: str, *_: object, **__: object) -> ChatResponse:
        calls.append(provider)
        if provider == "opencode_zen_account_1":
            raise ChatError("slot sem segredo", kind=ChatErrorKind.CONFIG)
        return response

    with (
        patch("app.integrations.fallback._call_provider", new=call_provider),
        patch("app.integrations.fallback._is_circuit_open", new=AsyncMock(return_value=False)),
        patch("app.integrations.fallback._record_failure", new=AsyncMock()) as record_failure,
        patch("app.integrations.fallback._record_success", new=AsyncMock()),
    ):
        result = await chat_with_fallback(
            [{"role": "user", "content": "olá"}],
            consent_granted=True,
            chain=["opencode_zen_account_1", "opencode_zen_account_2"],
        )

    assert result is response
    assert calls == ["opencode_zen_account_1", "opencode_zen_account_2"]
    record_failure.assert_not_awaited()


@pytest.mark.asyncio
async def test_zen_upstream_failure_opens_its_own_circuit_and_uses_next_slot() -> None:
    """Falhas de rede continuam isoladas por slot no circuit breaker Redis."""
    calls: list[str] = []
    response = ChatResponse("ok", "free-model-2", 1, 1, 1, "stop", 0, 0, None)

    async def call_provider(provider: str, *_: object, **__: object) -> ChatResponse:
        calls.append(provider)
        if provider == "opencode_zen_account_1":
            raise ChatError("timeout", kind=ChatErrorKind.TIMEOUT)
        return response

    with (
        patch("app.integrations.fallback._call_provider", new=call_provider),
        patch("app.integrations.fallback._is_circuit_open", new=AsyncMock(return_value=False)),
        patch("app.integrations.fallback._record_failure", new=AsyncMock()) as record_failure,
        patch("app.integrations.fallback._record_success", new=AsyncMock()),
    ):
        result = await chat_with_fallback(
            [{"role": "user", "content": "olá"}],
            consent_granted=True,
            chain=["opencode_zen_account_1", "opencode_zen_account_2"],
        )

    assert result is response
    assert calls == ["opencode_zen_account_1", "opencode_zen_account_2"]
    record_failure.assert_awaited_once_with("opencode_zen_account_1")
