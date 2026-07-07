"""Testes para app/integrations/jules.py (SQUAD C cobertura).

Cobre:
1. _scrub_messages: mascara PII em mensagens antes de enviar pro Jules
2. _flatten_messages_to_prompt: serializa mensagens no formato Jules prompt
3. chat_with_settings: happy path com httpx mock + LGPD_BLOCKED + CONFIG
4. Cobertura 17% -> meta >=70%
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.integrations.jules import (
    _flatten_messages_to_prompt,
    _scrub_messages,
    chat_with_settings,
)
from app.integrations.opencode_go import ChatErrorKind


def test_scrub_messages_mascara_cpf() -> None:
    """CPF nas mensagens eh mascarado antes de enviar pro Jules."""
    msgs = [
        {"role": "user", "content": "Meu CPF eh 123.456.789-09"},
    ]
    scrubbed, pii_count = _scrub_messages(msgs)
    assert pii_count >= 1
    assert "123.456.789-09" not in scrubbed[0]["content"]


def test_scrub_messages_preserva_estrutura_quando_sem_pii() -> None:
    """Mensagens sem PII sao preservadas identicas."""
    msgs = [
        {"role": "system", "content": "Voce eh um assistente"},
        {"role": "user", "content": "Ola, tudo bem?"},
    ]
    scrubbed, pii_count = _scrub_messages(msgs)
    assert pii_count == 0
    assert scrubbed[0]["content"] == "Voce eh um assistente"
    assert scrubbed[1]["content"] == "Ola, tudo bem?"


def test_flatten_messages_to_prompt_concatena_com_sep() -> None:
    """Mensagens sao concatenadas com prefixo [ROLE] e \\n\\n separador."""
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user msg"},
    ]
    prompt = _flatten_messages_to_prompt(msgs)
    assert "[SYSTEM]" in prompt
    assert "sys" in prompt
    assert "[USER]" in prompt
    assert "user msg" in prompt
    # Separador duplo newline entre mensagens
    assert "\n\n" in prompt


def test_flatten_messages_empty_retorna_vazio() -> None:
    """Lista vazia retorna string vazia."""
    assert _flatten_messages_to_prompt([]) == ""


def test_chat_with_settings_sem_consentimento_levanta_LGPD_BLOCKED() -> None:
    """LGPD art. 7 I: sem consentimento -> ChatError LGPD_BLOCKED (sem chamar rede)."""
    import asyncio

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=False,  # SEM consentimento
                actor_id="user-test",
                jules_api_key="dummy-key",
            )
        # Verifica que eh ChatError com kind LGPD_BLOCKED
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED

    asyncio.run(_run())


def test_chat_with_settings_sem_api_key_levanta_CONFIG() -> None:
    """Sem JULES_API_KEY -> ChatError CONFIG (sem chamar rede)."""
    import asyncio
    import os

    os.environ.pop("JULES_API_KEY", None)

    async def _run() -> None:
        with pytest.raises(Exception) as exc_info:
            await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="user-test",
                jules_api_key=None,  # sem key
            )
        from app.integrations.opencode_go import ChatError

        assert isinstance(exc_info.value, ChatError)
        assert exc_info.value.kind == ChatErrorKind.CONFIG

    asyncio.run(_run())


def test_chat_with_settings_POST_falha_4xx_levanta_HTTP_4XX() -> None:
    """Jules retorna 401 -> ChatError HTTP_4XX."""
    import asyncio

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> object:
            class FakeResp:
                status_code = 401
                text = "Unauthorized"

            return FakeResp()

    async def _run() -> None:
        with patch("app.integrations.jules.httpx.AsyncClient", FakeAsyncClient):
            with pytest.raises(Exception) as exc_info:
                await chat_with_settings(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                    actor_id="user-test",
                    jules_api_key="dummy",
                    poll_timeout_sec=0.1,  # fail-fast
                    poll_interval_sec=0.05,
                )
            from app.integrations.opencode_go import ChatError

            assert isinstance(exc_info.value, ChatError)
            assert exc_info.value.kind == ChatErrorKind.HTTP_4XX
            assert exc_info.value.status_code == 401

    asyncio.run(_run())
