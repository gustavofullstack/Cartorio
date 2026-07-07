"""Testes adicionais para app/integrations/opencode_generic.py - happy path + parse.

Cobre:
1. chat() happy path: retorna ChatResponse com content + tokens + PII scrubbed
2. chat() parse error: response nao e JSON
3. chat() parse error: estrutura inesperada (sem choices[0])
4. chat() timeout: httpx.TimeoutException -> ChatError TIMEOUT
5. chat() network: httpx.HTTPError -> ChatError NETWORK
6. chat() happy path com finish_reason

Sobe opencode_generic.py 52% -> >=75%.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.integrations.opencode_generic import ProviderConfig, chat
from app.integrations.opencode_go import ChatErrorKind


def test_chat_happy_path_retorna_ChatResponse_com_scrub_pii() -> None:
    """chat() happy path: retorna ChatResponse com PII scrubbed."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    fake_json = {
        "choices": [
            {"message": {"content": "Ola cliente 123.456.789-09"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "minimax-m3",
    }

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return fake_json

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
        with patch("httpx.AsyncClient", FakeClient):
            resp = await chat(
                [{"role": "user", "content": "Ola"}],
                config=cfg,
                consent_granted=True,
            )
            from app.integrations.opencode_go import ChatResponse

            assert isinstance(resp, ChatResponse)
            # PII (CPF) deve ser scrubbed na output
            assert "123.456.789-09" not in resp.content
            # Uso retornado
            assert resp.tokens_in == 10
            assert resp.tokens_out == 5
            assert resp.model == "minimax-m3"
            assert resp.finish_reason == "stop"
            # Latency registrada
            assert resp.latency_ms >= 0

    asyncio.run(_run())


def test_chat_parse_error_quando_response_nao_e_json() -> None:
    """Response com JSON invalido -> ChatError PARSE."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    class FakeResp:
        status_code = 200
        text = "not valid json {"

        def json(self) -> dict:
            raise ValueError("not json")

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
        with patch("httpx.AsyncClient", FakeClient):
            with pytest.raises(Exception) as exc_info:
                await chat(
                    [{"role": "user", "content": "oi"}],
                    config=cfg,
                    consent_granted=True,
                )
            from app.integrations.opencode_go import ChatError

            assert isinstance(exc_info.value, ChatError)
            assert exc_info.value.kind == ChatErrorKind.PARSE

    asyncio.run(_run())


def test_chat_parse_error_quando_estrutura_inesperada() -> None:
    """Response JSON sem choices[0].message -> ChatError PARSE."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    fake_json = {"unexpected": "format"}  # sem choices

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return fake_json

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
        with patch("httpx.AsyncClient", FakeClient):
            with pytest.raises(Exception) as exc_info:
                await chat(
                    [{"role": "user", "content": "oi"}],
                    config=cfg,
                    consent_granted=True,
                )
            from app.integrations.opencode_go import ChatError

            assert isinstance(exc_info.value, ChatError)
            assert exc_info.value.kind == ChatErrorKind.PARSE

    asyncio.run(_run())


def test_chat_timeout_levanta_ChatError_TIMEOUT() -> None:
    """httpx.TimeoutException -> ChatError TIMEOUT."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    import httpx

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> object:
            raise httpx.TimeoutException("timed out")

    async def _run() -> None:
        with patch("httpx.AsyncClient", FakeClient):
            with pytest.raises(Exception) as exc_info:
                await chat(
                    [{"role": "user", "content": "oi"}],
                    config=cfg,
                    consent_granted=True,
                )
            from app.integrations.opencode_go import ChatError

            assert isinstance(exc_info.value, ChatError)
            assert exc_info.value.kind == ChatErrorKind.TIMEOUT

    asyncio.run(_run())


def test_chat_network_error_levanta_ChatError_NETWORK() -> None:
    """httpx.HTTPError generico -> ChatError NETWORK."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    import httpx

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> object:
            raise httpx.ConnectError("connection refused")

    async def _run() -> None:
        with patch("httpx.AsyncClient", FakeClient):
            with pytest.raises(Exception) as exc_info:
                await chat(
                    [{"role": "user", "content": "oi"}],
                    config=cfg,
                    consent_granted=True,
                )
            from app.integrations.opencode_go import ChatError

            assert isinstance(exc_info.value, ChatError)
            assert exc_info.value.kind == ChatErrorKind.NETWORK

    asyncio.run(_run())


def test_chat_pii_scrubbed_in_output_quando_LLM_vaza_CPF() -> None:
    """LLM vaza CPF no output -> scrub remove PII antes de retornar (LGPD-015)."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    fake_json = {
        "choices": [
            {
                "message": {
                    "content": "Detectei que o cliente 123.456.789-09 esta com pendencia.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return fake_json

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
        with patch("httpx.AsyncClient", FakeClient):
            resp = await chat(
                [{"role": "user", "content": "oi"}],
                config=cfg,
                consent_granted=True,
            )
            # output_pii_redacted_count >= 1 (CPF foi scrubbed)
            assert resp.output_pii_redacted_count >= 1
            # CPF NAO aparece no content retornado
            assert "123.456.789-09" not in resp.content

    asyncio.run(_run())


def test_chat_input_pii_scrubbed_antes_de_enviar() -> None:
    """Mensagem de input com CPF eh scrubbed antes do POST (defense-in-depth)."""
    cfg = ProviderConfig(
        name="ok_provider",
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
    )

    captured: dict = {}

    fake_json = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return fake_json

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            captured["payload"] = kwargs.get("json", {})
            captured["headers"] = kwargs.get("headers", {})
            return FakeResp()

    async def _run() -> None:
        with patch("httpx.AsyncClient", FakeClient):
            resp = await chat(
                [{"role": "user", "content": "Meu CPF eh 123.456.789-09"}],
                config=cfg,
                consent_granted=True,
            )
            # Mensagem de input NAO carrega CPF cru ate o provider
            payload_messages = captured["payload"]["messages"]
            user_msg = next(m for m in payload_messages if m["role"] == "user")
            assert "123.456.789-09" not in user_msg["content"]
            # pii_redacted_count registrado
            assert resp.pii_redacted_count >= 1
            # Authorization header
            assert "Authorization" in captured["headers"]
            assert "Bearer" in captured["headers"]["Authorization"]
            # User-Agent forcado (Cloudflare fix lesson)
            assert "Mozilla" in captured["headers"]["User-Agent"]

    asyncio.run(_run())
