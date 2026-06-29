"""Testes para fallback LLM (Opencode-Go -> OpenClaw)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse
from app.integrations.fallback import chat_with_fallback


@pytest.mark.asyncio
async def test_chat_with_fallback_success_primary():
    """Se o primario funcionar, retorna a resposta sem chamar o fallback."""
    mock_resp = ChatResponse(
        content="Ola primario",
        model="minimax-m3",
        tokens_in=10,
        tokens_out=15,
        latency_ms=100,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
        )

        assert res.content == "Ola primario"
        mock_primary.assert_called_once()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_triggers_fallback_on_rate_limit():
    """Se o primario retornar rate limit, executa o fallback com sucesso."""
    mock_resp = ChatResponse(
        content="Ola fallback",
        model="openclaw",
        tokens_in=10,
        tokens_out=15,
        latency_ms=100,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("Rate limit", kind=ChatErrorKind.RATE_LIMITED)
        mock_fallback.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
        )

        assert res.content == "Ola fallback"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_no_fallback_on_consent_blocked():
    """Se o primario falhar com LGPD_BLOCKED, nao executa o fallback."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("LGPD Blocked", kind=ChatErrorKind.LGPD_BLOCKED)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=False,
            )

        assert exc.value.kind == ChatErrorKind.LGPD_BLOCKED
        mock_primary.assert_called_once()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_raises_if_all_fail():
    """Se todos os provedores (primary + fallback + tertiary/jules) falharem, propaga."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback, \
         patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules:
        mock_primary.side_effect = ChatError("Network primary", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = ChatError("Network fallback", kind=ChatErrorKind.NETWORK)
        mock_jules.side_effect = ChatError("Jules timeout", kind=ChatErrorKind.TIMEOUT)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=True,
            )

        assert "Jules timeout" in str(exc.value)
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()
        mock_jules.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_openclaw_as_primary():
    """Se primary_provider for openclaw, chama openclaw diretamente."""
    mock_resp = ChatResponse(
        content="Ola openclaw primary",
        model="openclaw",
        tokens_in=5,
        tokens_out=10,
        latency_ms=80,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_openclaw:
        mock_openclaw.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            primary_provider="openclaw",
            consent_granted=True,
        )

        assert res.content == "Ola openclaw primary"
        mock_openclaw.assert_called_once()
        mock_primary.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_unknown_primary_provider():
    """Provider primario desconhecido -> CONFIG error."""
    with pytest.raises(ChatError) as exc:
        await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            primary_provider="gpt-blabla",
            consent_granted=True,
        )
    assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_with_fallback_unknown_fallback_provider():
    """Provider fallback desconhecido -> CONFIG error do fallback."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("boom", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = ChatError("bad config", kind=ChatErrorKind.CONFIG)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                primary_provider="opencode_go",
                fallback_provider="openclaw",
                consent_granted=True,
            )
        assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_opencode_as_fallback():
    """Se fallback_provider for opencode_go, usa-o no fallback."""
    mock_resp = ChatResponse(
        content="voltei via opencode",
        model="minimax-m3",
        tokens_in=5,
        tokens_out=10,
        latency_ms=200,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_opencode, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_openclaw:
        # primary = openclaw, fallback = opencode
        mock_openclaw.side_effect = ChatError("openclaw down", kind=ChatErrorKind.NETWORK)
        mock_opencode.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            primary_provider="openclaw",
            fallback_provider="opencode_go",
            consent_granted=True,
        )
        assert res.content == "voltei via opencode"
        mock_openclaw.assert_called_once()
        mock_opencode.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_no_fallback_on_config_error():
    """Se o primario falhar com CONFIG, nao faz fallback."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback:
        mock_primary.side_effect = ChatError("missing key", kind=ChatErrorKind.CONFIG)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=False,
            )
        assert exc.value.kind == ChatErrorKind.CONFIG
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_unexpected_error_in_fallback():
    """Erro inesperado (nao ChatError) no fallback wrappeado em ChatError NETWORK
    e continua o chain para o tertiary. Ultimo erro eh propagado."""
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback, \
         patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules:
        mock_primary.side_effect = ChatError("primary", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = RuntimeError("kaboom")
        mock_jules.side_effect = ChatError("Jules config missing", kind=ChatErrorKind.CONFIG)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
            )
        # O CONFIG de jules deve parar chain imediatamente (LGPD_BLOCKED/CONFIG bail)
        assert exc.value.kind == ChatErrorKind.CONFIG
        mock_jules.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_records_audit_on_success():
    """Quando fallback tem sucesso E db esta setado, registra audit log."""
    from unittest.mock import MagicMock

    mock_resp = ChatResponse(
        content="ok fallback",
        model="openclaw",
        tokens_in=1,
        tokens_out=2,
        latency_ms=50,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    db = MagicMock()
    with patch("app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock) as mock_primary, \
         patch("app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock) as mock_fallback, \
         patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules, \
         patch("app.services.audit.AuditService.log") as mock_audit:
        mock_primary.side_effect = ChatError("rate", kind=ChatErrorKind.RATE_LIMITED)
        mock_fallback.return_value = mock_resp
        # jules NAO deve ser chamado (fallback retornou sucesso no step 1)

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            db=db,
            actor_id="agent-x",
            request_id="req-1",
            client_ip="127.0.0.1",
        )
        assert res.content == "ok fallback"
        mock_audit.assert_called_once()
        kwargs = mock_audit.call_args.kwargs
        assert kwargs["action"] == "llm.fallback_triggered"
        assert kwargs["payload"]["primary_provider"] == "opencode_go"
        assert kwargs["payload"]["fallback_chain"] == ["opencode_go", "openclaw"]
        assert kwargs["payload"]["previous_error_kind"] == "RATE_LIMITED"
        assert kwargs["payload"]["chain_step"] == 1
        mock_jules.assert_not_called()
