"""E2E Fallback chain 3x tests (T69, T70 + 1 extra, lesson 156, 2026-07-09).

Cobre 3 cenarios de fallback LLM (LiteLLM proxy on cartorio_litellm-app:4000):
  T69: LiteLLM UP   -> retorna resposta sem chamar fallback opencode_free_1
  T70: LiteLLM DOWN -> cai para opencode_free_1 (opencode_generic)
  T-extra: TODOS DOWN -> levanta ChatError

Patch no nivel de `_call_provider` para diferenciar providers (ambos usam
`opencode_generic.chat` por baixo, entao patching so `chat` nao discrimina).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse


# =============================================================================
# Helpers
# =============================================================================


def _fake_response(content: str, model: str = "minimax-m3") -> ChatResponse:
    """Cria ChatResponse de teste."""
    return ChatResponse(
        content=content,
        model=model,
        tokens_in=10,
        tokens_out=20,
        latency_ms=100,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )


def _make_provider_dispatch(*, litellm_response: ChatResponse | None = None,
                            litellm_error: Exception | None = None,
                            opencode_response: ChatResponse | None = None,
                            opencode_error: Exception | None = None,
                            openclaw_response: ChatResponse | None = None,
                            openclaw_error: Exception | None = None):
    """Cria funcao que simula `_call_provider` discriminando por nome.

    Cada provider eh tratado independentemente conforme os parametros.
    """
    async def fake_call_provider(provider: str, *args, **kwargs):
        if provider == "litellm":
            if litellm_error:
                raise litellm_error
            return litellm_response or _fake_response("LiteLLM default")
        if provider in ("opencode_free_1", "opencode_free_2", "opencode_free_3",
                        "opencode_go", "openrouter", "groq", "mistral", "google_ai_studio"):
            if opencode_error:
                raise opencode_error
            return opencode_response or _fake_response("opencode default")
        if provider == "openclaw":
            if openclaw_error:
                raise openclaw_error
            return openclaw_response or _fake_response("openclaw default")
        raise ChatError(f"Provider {provider} nao mockado", kind=ChatErrorKind.CONFIG)

    return fake_call_provider


# =============================================================================
# T69: LiteLLM UP -> retorna resposta sem tentar opencode_free_1
# =============================================================================


class TestFallbackLiteLLMUp:
    """T69: LiteLLM esta saudavel -> chain para no primeiro passo."""

    @pytest.mark.asyncio
    async def test_litellm_up_no_fallback_called(self) -> None:
        """Se LiteLLM retorna, opencode_free_1 NAO eh chamado."""
        from app.integrations.fallback import chat_with_fallback

        litellm_resp = _fake_response("Resposta do LiteLLM", model="gpt-4o-mini")
        opencode_resp = _fake_response("NAO DEVE RODAR", model="opencode")

        call_provider = _make_provider_dispatch(
            litellm_response=litellm_resp,
            opencode_response=opencode_resp,
        )

        # Track que opencode nao foi acessado via wrapper
        opencode_called = False
        original = call_provider

        async def tracked(provider, *a, **kw):
            nonlocal opencode_called
            if provider != "litellm":
                opencode_called = True
            return await original(provider, *a, **kw)

        with patch("app.integrations.fallback._call_provider", new=tracked):
            res = await chat_with_fallback(
                messages=[{"role": "user", "content": "Oi"}],
                consent_granted=True,
                chain=["litellm", "opencode_free_1"],
            )

        assert res.content == "Resposta do LiteLLM"
        assert res.model == "gpt-4o-mini"
        assert opencode_called is False, "opencode_free_1 nao deveria ter sido chamado"

    @pytest.mark.asyncio
    async def test_litellm_up_with_full_pipeline(self) -> None:
        """E2E real: chat_pipeline.call_llm_with_fallback -> LiteLLM UP."""
        from app.services.chat_pipeline import call_llm_with_fallback

        # Mock no chat_with_fallback direto (que eh chamado por call_llm_with_fallback)
        litellm_resp = _fake_response("Ola! Como posso ajudar?", model="gpt-4o-mini")

        with patch(
            "app.integrations.fallback._call_provider",
            new=_make_provider_dispatch(litellm_response=litellm_resp),
        ):
            resp_text = await call_llm_with_fallback(
                "Oi", consent_granted=True, actor_id="test:e2e", fast_path=True
            )

        assert isinstance(resp_text, str)
        assert len(resp_text) > 0


# =============================================================================
# T70: LiteLLM DOWN -> fallback opencode_free_1
# =============================================================================


class TestFallbackLiteLLMDown:
    """T70: LiteLLM retorna erro 500/network -> chain continua para opencode_free_1."""

    @pytest.mark.asyncio
    async def test_litellm_down_triggers_opencode_free_1(self) -> None:
        """LiteLLM falha com NETWORK -> opencode_free_1 responde."""
        from app.integrations.fallback import chat_with_fallback

        litellm_error = ChatError("Connection refused", kind=ChatErrorKind.NETWORK)
        opencode_resp = _fake_response("Resposta do opencode_free_1", model="deepseek-v3")

        # Track das chamadas
        calls: list[str] = []

        async def tracked(provider, *a, **kw):
            calls.append(provider)
            if provider == "litellm":
                raise litellm_error
            return opencode_resp

        with patch("app.integrations.fallback._call_provider", new=tracked):
            res = await chat_with_fallback(
                messages=[{"role": "user", "content": "Test"}],
                consent_granted=True,
                chain=["litellm", "opencode_free_1"],
            )

        assert res.content == "Resposta do opencode_free_1"
        assert res.model == "deepseek-v3"
        # Verifica ordem
        assert calls == ["litellm", "opencode_free_1"]

    @pytest.mark.asyncio
    async def test_litellm_4xx_skips_to_opencode_free_1(self) -> None:
        """LiteLLM retorna 4xx (raro) -> tenta opencode_free_1."""
        from app.integrations.fallback import chat_with_fallback

        async def fail_then_opencode(provider, *a, **kw):
            if provider == "litellm":
                raise ChatError("Rate limit", kind=ChatErrorKind.RATE_LIMITED)
            return _fake_response("Resposta fallback")

        with patch("app.integrations.fallback._call_provider", new=fail_then_opencode):
            res = await chat_with_fallback(
                messages=[{"role": "user", "content": "Test"}],
                consent_granted=True,
                chain=["litellm", "opencode_free_1"],
            )

        assert res.content == "Resposta fallback"

    @pytest.mark.asyncio
    async def test_litellm_down_then_openclaw(self) -> None:
        """LiteLLM DOWN, opencode_free_1 DOWN, openclaw UP -> 3rd no chain responde."""
        from app.integrations.fallback import chat_with_fallback

        async def chain_3rd(provider, *a, **kw):
            if provider in ("litellm", "opencode_free_1"):
                raise ChatError(f"{provider} down", kind=ChatErrorKind.NETWORK)
            return _fake_response("openclaw respondeu", model="gpt-5.5")

        with patch("app.integrations.fallback._call_provider", new=chain_3rd):
            res = await chat_with_fallback(
                messages=[{"role": "user", "content": "Test"}],
                consent_granted=True,
                chain=["litellm", "opencode_free_1", "openclaw"],
            )

        assert res.content == "openclaw respondeu"


# =============================================================================
# T-extra: TODOS providers DOWN -> ChatError
# =============================================================================


class TestFallbackAllDown:
    """Todos os providers da chain falham -> deve levantar ChatError."""

    @pytest.mark.asyncio
    async def test_all_providers_down_raises_chat_error(self) -> None:
        from app.integrations.fallback import chat_with_fallback

        async def always_fail(provider, *a, **kw):
            raise ChatError("Service unavailable", kind=ChatErrorKind.NETWORK)

        with patch("app.integrations.fallback._call_provider", new=always_fail):
            with pytest.raises(ChatError) as exc_info:
                await chat_with_fallback(
                    messages=[{"role": "user", "content": "Test"}],
                    consent_granted=True,
                    chain=["litellm", "opencode_free_1"],
                )

        # Erro do ultimo provider
        assert exc_info.value.kind == ChatErrorKind.NETWORK

    @pytest.mark.asyncio
    async def test_lgpd_blocked_aborts_chain(self) -> None:
        """LGPD_BLOCKED antes do chain deve abortar tudo (raise imediato)."""
        from app.integrations.fallback import chat_with_fallback

        # Sem mocks — fluxo real deve detectar LGPD blocked
        with pytest.raises(ChatError) as exc_info:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "Test"}],
                consent_granted=False,  # LGPD BLOCKED
                chain=["litellm", "opencode_free_1"],
            )

        assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED

    @pytest.mark.asyncio
    async def test_pipeline_returns_manutencao_message_when_all_down(self) -> None:
        """chat_pipeline.call_llm_with_fallback deve retornar msg amigavel quando tudo cai."""
        from app.services.chat_pipeline import call_llm_with_fallback

        async def always_fail(*args, **kwargs):
            raise ChatError("todas as providers offline", kind=ChatErrorKind.NETWORK)

        with patch("app.integrations.fallback._call_provider", new=always_fail):
            # Quando ChatError eh lancado, chat_pipeline captura e retorna msg amigavel
            resp_text = await call_llm_with_fallback(
                "Oi", consent_granted=True, actor_id="test:e2e"
            )
            # Deve retornar texto de manutencao (LGPD-safe)
            assert "manutencao" in resp_text.lower() or "atendimento" in resp_text.lower()
