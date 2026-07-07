"""Testes para fallback LLM (Opencode-Go -> OpenClaw)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
    ):
        mock_primary.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
            chain=["opencode_go", "openclaw"],
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
    ):
        mock_primary.side_effect = ChatError("Rate limit", kind=ChatErrorKind.RATE_LIMITED)
        mock_fallback.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "teste"}],
            consent_granted=True,
            chain=["opencode_go", "openclaw"],
        )

        assert res.content == "Ola fallback"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_no_fallback_on_consent_blocked():
    """Se o primario falhar com LGPD_BLOCKED, nao executa o fallback."""
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
    ):
        mock_primary.side_effect = ChatError("LGPD Blocked", kind=ChatErrorKind.LGPD_BLOCKED)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=False,
                chain=["opencode_go", "openclaw"],
            )

        assert exc.value.kind == ChatErrorKind.LGPD_BLOCKED
        mock_primary.assert_not_called()
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_raises_if_all_fail():
    """Se todos os provedores (primary + fallback + tertiary/jules) falharem, propaga."""
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
        patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules,
    ):
        mock_primary.side_effect = ChatError("Network primary", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = ChatError("Network fallback", kind=ChatErrorKind.NETWORK)
        mock_jules.side_effect = ChatError("Jules timeout", kind=ChatErrorKind.TIMEOUT)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "teste"}],
                consent_granted=True,
                chain=["opencode_go", "openclaw", "jules"],
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_openclaw,
    ):
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
    ):
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_opencode,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_openclaw,
    ):
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
    ):
        mock_primary.side_effect = ChatError("missing key", kind=ChatErrorKind.CONFIG)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=["opencode_go", "openclaw"],
            )
        assert exc.value.kind == ChatErrorKind.CONFIG
        mock_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_unexpected_error_in_fallback():
    """Erro inesperado (nao ChatError) no fallback wrappeado em ChatError NETWORK
    e continua o chain para o tertiary. Ultimo erro eh propagado."""
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
        patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules,
    ):
        mock_primary.side_effect = ChatError("primary", kind=ChatErrorKind.NETWORK)
        mock_fallback.side_effect = RuntimeError("kaboom")
        mock_jules.side_effect = ChatError("Jules config missing", kind=ChatErrorKind.CONFIG)

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=["opencode_go", "openclaw", "jules"],
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
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch(
            "app.integrations.openclaw.chat_with_settings", new_callable=AsyncMock
        ) as mock_fallback,
        patch("app.integrations.jules.chat_with_settings", new_callable=AsyncMock) as mock_jules,
        patch("app.services.audit.AuditService.log") as mock_audit,
    ):
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
            chain=["opencode_go", "openclaw"],
        )
        assert res.content == "ok fallback"
        mock_audit.assert_called_once()
        kwargs = mock_audit.call_args.kwargs
        assert kwargs["action"] == "llm.call_success"
        assert kwargs["payload"]["provider"] == "openclaw"
        assert kwargs["payload"]["previous_failed_chain"] == ["opencode_go"]
        assert kwargs["payload"]["previous_error_kind"] == "RATE_LIMITED"
        assert kwargs["payload"]["chain_idx"] == 1
        mock_jules.assert_not_called()


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_generic_openai_provider():
    """Se o provedor for OpenAI-compat, deve despachar para chat_generic com sua config."""
    mock_resp = ChatResponse(
        content="ola generic",
        model="groq-model",
        tokens_in=5,
        tokens_out=5,
        latency_ms=150,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with (
        patch("app.integrations.opencode_generic.chat", new_callable=AsyncMock) as mock_generic,
        patch("app.integrations.opencode_generic.get_config_for") as mock_get_config,
    ):
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg
        mock_generic.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            chain=["groq"],
            model="custom-model",
        )
        assert res.content == "ola generic"
        assert mock_cfg.model == "custom-model"
        mock_generic.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_generic_provider_no_config():
    """Generic provider sem config deve levantar CONFIG error."""
    with patch("app.integrations.opencode_generic.get_config_for") as mock_get_config:
        mock_get_config.return_value = None

        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=["groq"],
            )
        assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_antigravity_provider():
    """Se o provedor for antigravity, deve despachar para chat_antigravity."""
    mock_resp = ChatResponse(
        content="ola antigravity",
        model="antigravity",
        tokens_in=5,
        tokens_out=5,
        latency_ms=150,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with (
        patch(
            "app.integrations.antigravity.chat_with_settings", new_callable=AsyncMock
        ) as mock_antigravity,
        patch("app.integrations.fallback._PROVIDER_ALIASES", {}),
    ):
        mock_antigravity.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            chain=["antigravity"],
        )
        assert res.content == "ola antigravity"
        mock_antigravity.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_defaults_to_settings_chain():
    """Se chain nao for informado, usa o llm_fallback_chain das settings."""
    mock_resp = ChatResponse(
        content="ola settings default",
        model="opencode_go",
        tokens_in=5,
        tokens_out=5,
        latency_ms=150,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch("app.config.settings") as mock_settings,
    ):
        mock_settings.llm_fallback_chain = "opencode_go,openclaw"
        mock_primary.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            chain=None,
        )
        assert res.content == "ola settings default"
        mock_primary.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_empty_chain_raises_config():
    """Chain vazia ou sem settings define CONFIG error."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.llm_fallback_chain = ""
        with pytest.raises(ChatError) as exc:
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=None,
            )
        assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_with_fallback_audit_log_success_raises_warning():
    """Falha de escrita no audit log em caso de sucesso nao quebra o fluxo principal."""
    mock_resp = ChatResponse(
        content="ola",
        model="opencode_go",
        tokens_in=5,
        tokens_out=5,
        latency_ms=150,
        finish_reason="stop",
        pii_redacted_count=0,
        output_pii_redacted_count=0,
    )
    db = MagicMock()
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch("app.services.audit.AuditService.log", side_effect=Exception("DB connection error")),
    ):
        mock_primary.return_value = mock_resp

        res = await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            chain=["opencode_go"],
            db=db,
        )
        assert res.content == "ola"


@pytest.mark.asyncio
async def test_chat_with_fallback_audit_log_total_failure():
    """Se toda a chain falhar, loga falha total de auditoria e propaga erro."""
    db = MagicMock()
    with (
        patch(
            "app.integrations.opencode_go.chat_with_settings", new_callable=AsyncMock
        ) as mock_primary,
        patch("app.services.audit.AuditService.log") as mock_audit,
    ):
        mock_primary.side_effect = ChatError("error", kind=ChatErrorKind.NETWORK)

        with pytest.raises(ChatError):
            await chat_with_fallback(
                messages=[{"role": "user", "content": "oi"}],
                consent_granted=True,
                chain=["opencode_go"],
                db=db,
            )
        assert mock_audit.call_count >= 1
        kwargs = mock_audit.call_args.kwargs
        assert kwargs["action"] == "llm.chain_total_failure"


@pytest.mark.asyncio
async def test_chat_with_fallback_unknown_provider_raises():
    """Roteamento para provedor nao existente levanta CONFIG error."""
    with pytest.raises(ChatError) as exc:
        await chat_with_fallback(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            chain=["invalid_provider"],
        )
    assert exc.value.kind == ChatErrorKind.CONFIG
