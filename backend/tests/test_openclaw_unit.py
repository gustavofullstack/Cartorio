"""Testes unitarios para app.integrations.openclaw (provider secundario).

Cobre:
- base_url ausente -> CONFIG
- messages vazio -> CONFIG
- consent nao granted -> LGPD_BLOCKED
- happy path com mock httpx
- HTTP 4xx/5xx
- response nao-JSON (PARSE)
- estrutura inesperada (PARSE)
- output PII scrubbing
- audit log via db
- rate limit check
- chat_with_settings wrapper
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.openclaw import chat, chat_with_settings
from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse


def _make_httpx_response(status_code: int, json_data: dict | None = None, text: str = ""):
    """Constroi um httpx.Response valido para mocks."""
    if json_data is not None:
        req = httpx.Request("POST", "http://test/x")
        return httpx.Response(status_code, json=json_data, request=req)
    req = httpx.Request("POST", "http://test/x")
    return httpx.Response(status_code, text=text, request=req)


@pytest.mark.asyncio
async def test_openclaw_chat_empty_base_url():
    """base_url vazia E settings vazia -> ChatError CONFIG."""
    # Garante que settings.openclaw_base_url tb e vazia para o teste.
    with patch("app.config.settings.openclaw_base_url", ""):
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_openclaw_chat_whitespace_base_url():
    """base_url so com whitespace -> ChatError CONFIG."""
    with patch("app.config.settings.openclaw_base_url", "   "):
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="   ",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_openclaw_chat_empty_messages():
    """messages vazio -> ChatError CONFIG."""
    with pytest.raises(ChatError) as exc:
        await chat(
            messages=[],
            base_url="http://localhost:8080",
            consent_granted=True,
        )
    assert exc.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_openclaw_chat_consent_blocked():
    """Sem consentimento -> ChatError LGPD_BLOCKED (LGPD art. 7 I)."""
    with pytest.raises(ChatError) as exc:
        await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:8080",
            consent_granted=False,
        )
    assert exc.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_openclaw_chat_happy_path():
    """Resposta 200 com JSON valido -> retorna ChatResponse com PII scrub."""
    payload = {
        "id": "cmpl-1",
        "model": "openclaw-pietra",
        "choices": [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "Ola, tudo bem?"}}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
        )
    assert isinstance(resp, ChatResponse)
    assert resp.content == "Ola, tudo bem?"
    assert resp.model == "openclaw-pietra"
    assert resp.tokens_in == 10
    assert resp.tokens_out == 5
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_openclaw_chat_http_4xx():
    """Resposta 401 do provider -> ChatError HTTP_4XX."""
    mock_resp = _make_httpx_response(401, text="Unauthorized")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.HTTP_4XX
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_openclaw_chat_http_5xx():
    """Resposta 503 do provider -> ChatError HTTP_5XX."""
    mock_resp = _make_httpx_response(503, text="Service Unavailable")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.HTTP_5XX
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_openclaw_chat_timeout():
    """httpx.TimeoutException -> ChatError TIMEOUT."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("too slow")
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
                timeout_seconds=1.0,
            )
    assert exc.value.kind == ChatErrorKind.TIMEOUT


@pytest.mark.asyncio
async def test_openclaw_chat_network_error():
    """httpx.HTTPError generico -> ChatError NETWORK."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("conn refused")
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.NETWORK


@pytest.mark.asyncio
async def test_openclaw_chat_invalid_json():
    """Response nao-JSON -> ChatError PARSE."""
    # httpx precisa de request pra montar um Response
    req = httpx.Request("POST", "http://test/x")
    bad = httpx.Response(200, text="not json at all{", request=req)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = bad
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.PARSE


@pytest.mark.asyncio
async def test_openclaw_chat_unexpected_structure():
    """JSON sem 'choices' -> ChatError PARSE."""
    bad = {"usage": {"prompt_tokens": 1, "completion_tokens": 1}}  # sem choices
    mock_resp = _make_httpx_response(200, json_data=bad)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(ChatError) as exc:
            await chat(
                messages=[{"role": "user", "content": "oi"}],
                base_url="http://localhost:18790",
                consent_granted=True,
            )
    assert exc.value.kind == ChatErrorKind.PARSE


@pytest.mark.asyncio
async def test_openclaw_chat_output_pii_scrubbed():
    """PII no output do LLM -> scrub via output PII layer + count > 0."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Meu CPF e 123.456.789-09",  # PII no output
                },
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
        )
    # PII deve ter sido removida do content
    assert "123.456.789-09" not in resp.content
    assert resp.output_pii_redacted_count > 0


@pytest.mark.asyncio
async def test_openclaw_chat_with_db_records_audit():
    """Com db fornecido, registra audit log via _audit_log_sync."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    db = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.integrations.openclaw._audit_log_sync") as mock_audit:
        mock_post.return_value = mock_resp
        await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
            db=db,
            actor_id="agent-x",
        )
        mock_audit.assert_called_once()
        kwargs = mock_audit.call_args.kwargs
        assert kwargs["action"] == "openclaw.chat"
        assert kwargs["resource"] == "llm:openclaw"
        assert kwargs["actor_id"] == "agent-x"


@pytest.mark.asyncio
async def test_openclaw_chat_with_db_and_output_pii_records_audit_twice():
    """PII no output + db -> registra audit chat E audit llm.output_scrubbed."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Tel 11999998888"},
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    db = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.integrations.openclaw._audit_log_sync") as mock_audit:
        mock_post.return_value = mock_resp
        await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
            db=db,
            actor_id="agent-x",
            request_id="req-1",
            client_ip="127.0.0.1",
        )
        # 1 chamada: openclaw.chat; 2 chamada: llm.output_scrubbed
        assert mock_audit.call_count == 2
        actions = [c.kwargs["action"] for c in mock_audit.call_args_list]
        assert "openclaw.chat" in actions
        assert "llm.output_scrubbed" in actions


@pytest.mark.asyncio
async def test_openclaw_chat_audit_log_failure_swallowed():
    """Falha no audit log NAO derruba a chamada (LGPD nao-bloqueante)."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    db = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.integrations.openclaw._audit_log_sync", side_effect=Exception("audit fail")):
        mock_post.return_value = mock_resp
        resp = await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
            db=db,
            actor_id="agent-x",
        )
    assert resp.content == "ok"


@pytest.mark.asyncio
async def test_openclaw_chat_with_rate_limit_invoked():
    """Se rate_limit_per_minute + session_id + redis_url -> chama _check_rate_limit."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.integrations.openclaw._check_rate_limit") as mock_rl:
        mock_post.return_value = mock_resp
        await chat(
            messages=[{"role": "user", "content": "oi"}],
            base_url="http://localhost:18790",
            consent_granted=True,
            session_id="sess-1",
            rate_limit_per_minute=60,
            redis_url="redis://localhost:6379/0",
        )
        mock_rl.assert_called_once_with("sess-1", 60, "redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_openclaw_chat_with_settings_wrapper():
    """chat_with_settings usa settings.openclaw_base_url/api_key/redis_url."""
    payload = {
        "model": "openclaw-pietra",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    mock_resp = _make_httpx_response(200, json_data=payload)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await chat_with_settings(
            messages=[{"role": "user", "content": "oi"}],
            consent_granted=True,
            actor_id="agent-x",
        )
    assert resp.content == "ok"