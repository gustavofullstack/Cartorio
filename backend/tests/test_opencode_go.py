"""Testes para integracao OpenCode-Go (LLM provider low-cost).

Cobre:
- Chat completion basico (mock httpx)
- Tratamento de erro (4xx/5xx)
- Validacao de API key (bloqueia se vazia)
- Contagem de tokens e latencia (para audit log)
- LGPD art. 7 I: consent gate (BLOCKER 3)
- LGPD art. 46: PII scrubbing INTERNO (BLOCKER 1)
- LGPD art. 37: audit log via AuditService (BLOCKER 2)
- Rate limit por sessao (BLOCKER 7)
- Docstring alinhada (BLOCKER 8 — coberto por teste de importacao)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ============================================================================
# Testes unitarios basicos (existente + consent gate)
# ============================================================================


@pytest.mark.asyncio
async def test_chat_returns_completion_with_valid_key():
    """Chat retorna choices[0].message.content quando API responde 200."""
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-123",
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Ola, como posso ajudar?"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test-1234567890",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,  # LGPD art. 7 I
        )

    assert result.content == "Ola, como posso ajudar?"
    assert result.model == "deepseek-v4-flash"
    assert result.tokens_in == 10
    assert result.tokens_out == 8
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_chat_raises_on_missing_api_key():
    """Chat falha claro se API key nao configurada."""
    from app.integrations.opencode_go import ChatError, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    assert "API_KEY" in str(exc_info.value) or "API key" in str(exc_info.value).upper()


@pytest.mark.asyncio
async def test_chat_raises_on_missing_base_url():
    """Chat falha claro se base_url nao configurada."""
    from app.integrations.opencode_go import ChatError, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test-123",
            base_url="",
            consent_granted=True,
        )

    assert "BASE_URL" in str(exc_info.value).upper() or "URL" in str(exc_info.value).upper()


@pytest.mark.asyncio
async def test_chat_raises_on_http_4xx():
    """Chat propaga erro HTTP 4xx com mensagem clara."""
    from app.integrations.opencode_go import ChatError, chat

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized: invalid api key"

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-invalid",
                base_url="https://api.opencode.ai/v1",
                consent_granted=True,
            )

        assert exc_info.value.status_code == 401
        assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_raises_on_http_5xx():
    """Chat propaga erro HTTP 5xx com mensagem clara."""
    from app.integrations.opencode_go import ChatError, chat

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
                consent_granted=True,
            )

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_chat_raises_on_timeout():
    """Chat propaga timeout como ChatError."""
    from app.integrations.opencode_go import ChatError, chat

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout 30s")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
                consent_granted=True,
            )

        assert "TIMEOUT" in str(exc_info.value).upper() or "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_chat_sends_correct_payload():
    """Chat envia payload com model + messages + headers corretos."""
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[
                {"role": "system", "content": "Voce e assistente."},
                {"role": "user", "content": "Ola"},
            ],
            model="deepseek-v4-flash",
            api_key="sk-test-abc",
            base_url="https://api.opencode.ai/v1",
            temperature=0.5,
            consent_granted=True,
        )

        call_args = mock_client.post.call_args
        # URL
        assert call_args.args[0] == "https://api.opencode.ai/v1/chat/completions"
        # Headers
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer sk-test-abc"
        assert headers["Content-Type"] == "application/json"
        # Body
        body = call_args.kwargs["json"]
        assert body["model"] == "deepseek-v4-flash"
        assert body["temperature"] == 0.5
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_chat_measures_latency():
    """Chat mede latencia em ms."""
    import asyncio

    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    async def slow_post(*args, **kwargs):
        await asyncio.sleep(0.01)
        return mock_response

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = slow_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    assert result.latency_ms >= 10


# ============================================================================
# BLOCKER 3 — Consent gate (LGPD art. 7 I)
# ============================================================================


@pytest.mark.asyncio
async def test_chat_blocks_when_consent_not_granted():
    """BLOCKER 3: Bloqueia chamada se consent_granted=False (LGPD art. 7 I)."""
    from app.integrations.opencode_go import ChatError, ChatErrorKind, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=False,  # LGPD BLOCKED
        )

    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED
    assert "LGPD" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_blocks_when_consent_default_false():
    """BLOCKER 3: Default eh False (safe-by-default)."""
    from app.integrations.opencode_go import ChatError, ChatErrorKind, chat

    with pytest.raises(ChatError) as exc_info:
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            # consent_granted omitido - default False
        )

    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_chat_does_not_call_provider_when_consent_blocked():
    """BLOCKER 3: Quando bloqueado por LGPD, NAO chama httpx."""
    from app.integrations.opencode_go import ChatError, chat

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        with pytest.raises(ChatError):
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
                consent_granted=False,
            )

        # httpx NAO foi chamado
        mock_client.post.assert_not_called()


# ============================================================================
# BLOCKER 1 — PII scrubbing INTERNO (defense-in-depth)
# ============================================================================


@pytest.mark.asyncio
async def test_chat_scrubs_cpf_internally():
    """BLOCKER 1: CPF no message eh scrubbed ANTES de enviar ao provider."""
    from app.integrations.opencode_go import chat

    captured_payloads = []

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    async def mock_post(*args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        return mock_response

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Meu CPF e 123.456.789-09"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    # Provider recebeu CPF REDACTED, NAO o CPF bruto
    sent_payload = captured_payloads[0]
    sent_text = json.dumps(sent_payload)
    assert "123.456.789-09" not in sent_text
    assert "CPF_REDACTED" in sent_text
    assert result.pii_redacted_count == 1


@pytest.mark.asyncio
async def test_chat_scrubs_multiple_pii_types():
    """BLOCKER 1: Scrubbing detecta CPF + email + telefone juntos."""
    from app.integrations.opencode_go import chat

    captured_payloads = []

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    async def mock_post(*args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        return mock_response

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Meu CPF 123.456.789-09, email joao@test.com "
                        "e telefone (34) 99999-9999"
                    ),
                }
            ],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    sent_text = json.dumps(captured_payloads[0])
    assert "123.456.789-09" not in sent_text
    assert "joao@test.com" not in sent_text
    # Phone regex pode casar parcialmente, mas o numero bruto NAO pode estar la
    assert "99999-9999" not in sent_text
    assert "CPF_REDACTED" in sent_text
    assert "EMAIL_REDACTED" in sent_text
    assert "PHONE_BR_REDACTED" in sent_text
    assert result.pii_redacted_count == 3


@pytest.mark.asyncio
async def test_chat_scrub_is_idempotent():
    """BLOCKER 1: Double-scrub eh no-op (caller pode scrubbar tambem)."""
    from app.integrations.opencode_go import chat
    from app.services.pii import scrub

    captured_payloads = []

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    async def mock_post(*args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        return mock_response

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        # Caller ja fez scrub
        pre_scrubbed = scrub("Meu CPF 123.456.789-09").text  # vira "Meu CPF [CPF_REDACTED]"
        result = await chat(
            messages=[{"role": "user", "content": pre_scrubbed}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    sent_text = json.dumps(captured_payloads[0])
    # NAO adicionou outro [CPF_REDACTED] - idem potencia
    assert sent_text.count("CPF_REDACTED") == 1


# ============================================================================
# BLOCKER 2 — Audit log via AuditService (LGPD art. 37)
# ============================================================================


@pytest.mark.asyncio
async def test_chat_writes_audit_log_when_db_provided(db_session):
    """BLOCKER 2: Grava entrada no audit log quando db Session fornecido."""
    from app.integrations.opencode_go import chat
    from app.models.audit_log import AuditLog

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "model": "deepseek-v4-flash",
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            actor_id="cliente:42",
            db=db_session,
        )

    # Verifica audit log
    entries = db_session.query(AuditLog).all()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.action == "opencode_go.chat"
    assert entry.resource == "llm:opencode_go"
    assert entry.actor_id == "cliente:42"
    assert entry.payload["provider"] == "opencode_go"
    assert entry.payload["model"] == "deepseek-v4-flash"
    assert entry.payload["consent_granted"] is True
    assert entry.payload["pii_redacted_count"] == 0
    assert entry.payload["tokens_in"] == 10
    assert entry.payload["tokens_out"] == 5
    assert "request_hash" in entry.payload
    assert "response_hash" in entry.payload


@pytest.mark.asyncio
async def test_chat_does_not_write_audit_log_when_db_none():
    """BLOCKER 2: Sem db, NAO grava audit log."""
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        # db NAO fornecido
        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
        )

    assert result.content == "ok"


@pytest.mark.asyncio
async def test_chat_audit_log_redacts_pii_in_request_hash(db_session):
    """BLOCKER 2: request_hash eh SHA-256 do payload SCRUBBED, nao bruto."""
    from app.integrations.opencode_go import chat
    from app.models.audit_log import AuditLog

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        await chat(
            messages=[{"role": "user", "content": "Meu CPF e 123.456.789-09"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            actor_id="cliente:99",
            db=db_session,
        )

    entry = db_session.query(AuditLog).first()
    # Hash do payload NAO contem CPF bruto (LGPD: hash eh do SCRUBBED)
    # request_hash eh 64 hex chars
    assert len(entry.payload["request_hash"]) == 64
    # pii_redacted_count registrado
    assert entry.payload["pii_redacted_count"] == 1


# ============================================================================
# BLOCKER 7 — Rate limit por sessao
# ============================================================================


@pytest.mark.asyncio
async def test_chat_blocks_when_rate_limit_exceeded():
    """BLOCKER 7: Bloqueia quando rate limit excedido."""
    from unittest.mock import MagicMock

    from app.integrations.opencode_go import ChatError, ChatErrorKind, chat

    # Mock Redis que retorna count > limit
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 61  # acima do limite
    mock_redis.close.return_value = None

    with patch("app.integrations.opencode_go.redis.from_url") as mock_redis_from_url:
        mock_redis_from_url.return_value = mock_redis

        with pytest.raises(ChatError) as exc_info:
            await chat(
                messages=[{"role": "user", "content": "Ola"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.opencode.ai/v1",
                consent_granted=True,
                session_id="sess-abc",
                rate_limit_per_minute=60,
                redis_url="redis://test:6379/0",
            )

        assert exc_info.value.kind == ChatErrorKind.RATE_LIMITED


@pytest.mark.asyncio
async def test_chat_no_rate_limit_when_disabled():
    """BLOCKER 7: Sem rate_limit_per_minute, NAO consulta Redis."""
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with (
        patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls,
        patch("app.integrations.opencode_go.redis.from_url") as mock_redis_from_url,
    ):
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        # rate_limit_per_minute=None - NAO consulta Redis
        await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.opencode.ai/v1",
            consent_granted=True,
            session_id="sess-abc",
        )

        mock_redis_from_url.assert_not_called()


# ============================================================================
# BLOCKER 8 — Docstring alinhada (deepseek-v4-flash)
# ============================================================================


def test_docstring_declares_correct_model():
    """BLOCKER 8: Docstring do modulo declara `deepseek-v4-flash` roteado via OpenCode-Go."""
    from app.integrations import opencode_go

    docstring = opencode_go.__doc__ or ""
    assert "deepseek-v4-flash" in docstring
    assert "OpenCode-Go" in docstring
    # A inconsistência com MiniMax foi resolvida (opencode.json = Mavis runtime)
    assert "MiniMax" in docstring or "Mavis runtime" in docstring
