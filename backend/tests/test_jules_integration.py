"""Testes para app/integrations/jules.py (SQUAD C cobertura).

Cobre:
1. _scrub_messages: mascara PII em mensagens antes de enviar pro Jules
2. _flatten_messages_to_prompt: serializa mensagens no formato Jules prompt
3. chat_with_settings: happy path, timeouts, status erros, exception handling, audit log, PII log.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

from app.integrations.jules import (
    _flatten_messages_to_prompt,
    _scrub_messages,
    chat_with_settings,
)
from app.integrations.opencode_go import ChatError, ChatErrorKind


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
        {"role": "assistant", "content": "assistant msg"},
        {"role": "user", "content": "user msg"},
    ]
    prompt = _flatten_messages_to_prompt(msgs)
    assert "[SYSTEM]\nsys" in prompt
    assert "[ASSISTANT]\nassistant msg" in prompt
    assert "[USER]\nuser msg" in prompt
    assert "\n\n" in prompt


def test_flatten_messages_empty_retorna_vazio() -> None:
    """Lista vazia retorna string vazia."""
    assert _flatten_messages_to_prompt([]) == ""


@pytest.mark.asyncio
async def test_chat_with_settings_sem_consentimento_levanta_LGPD_BLOCKED() -> None:
    """LGPD art. 7 I: sem consentimento -> ChatError LGPD_BLOCKED (sem chamar rede)."""
    with pytest.raises(ChatError) as exc_info:
        await chat_with_settings(
            [{"role": "user", "content": "oi"}],
            consent_granted=False,
            actor_id="user-test",
            jules_api_key="dummy-key",
        )
    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_chat_with_settings_sem_api_key_levanta_CONFIG(monkeypatch) -> None:
    """Sem JULES_API_KEY -> ChatError CONFIG (sem chamar rede)."""
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    with pytest.raises(ChatError) as exc_info:
        await chat_with_settings(
            [{"role": "user", "content": "oi"}],
            consent_granted=True,
            actor_id="user-test",
            jules_api_key=None,
        )
    assert exc_info.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_with_settings_POST_falha_4xx_levanta_HTTP_4XX() -> None:
    """Jules retorna 401 -> ChatError HTTP_4XX."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="user-test",
                jules_api_key="dummy",
            )
        assert exc_info.value.kind == ChatErrorKind.HTTP_4XX
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_chat_with_settings_happy_path() -> None:
    """Jules session criada e polling retorna resposta com sucesso."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"id": "session-123"}

    activities_resp = MagicMock()
    activities_resp.status_code = 200
    activities_resp.json.return_value = {
        "activities": [
            {
                "originator": "agent",
                "agentMessaged": {"agentMessage": "Ola! Como posso ajudar?"},
            }
        ]
    }

    mock_db = MagicMock(spec=Session)

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=activities_resp)):
            with patch("app.services.audit.AuditService.log") as mock_audit:
                resp = await chat_with_settings(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                    actor_id="user-test",
                    jules_api_key="dummy",
                    poll_timeout_sec=1.0,
                    poll_interval_sec=0.01,
                    db=mock_db,
                )
                assert resp.content == "Ola! Como posso ajudar?"
                assert resp.model == "jules"
                assert mock_audit.call_count >= 1


@pytest.mark.asyncio
async def test_chat_with_settings_happy_path_com_pii() -> None:
    """Jules session com PII no output dispara log extra de PII scrubbed."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"name": "projects/123/sessions/session-456"}

    activities_resp = MagicMock()
    activities_resp.status_code = 200
    activities_resp.json.return_value = {
        "activities": [
            {
                "originator": "agent",
                "agentMessaged": {"agentMessage": "O CPF e 123.456.789-09"},
            }
        ]
    }

    mock_db = MagicMock(spec=Session)

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=activities_resp)):
            with patch("app.services.audit.AuditService.log") as mock_audit:
                resp = await chat_with_settings(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                    actor_id="user-test",
                    jules_api_key="dummy",
                    poll_timeout_sec=1.0,
                    poll_interval_sec=0.01,
                    db=mock_db,
                )
                assert "123.456.789-09" not in resp.content
                assert resp.output_pii_redacted_count >= 1
                # Deve chamar log de auditoria normal + log extra de output_scrubbed
                assert mock_audit.call_count >= 2


@pytest.mark.asyncio
async def test_chat_with_settings_post_network_error() -> None:
    """POST session levanta erro de rede -> ChatError NETWORK."""
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.HTTPError("net error"))):
        with pytest.raises(ChatError) as exc_info:
            await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="user-test",
                jules_api_key="dummy",
            )
        assert exc_info.value.kind == ChatErrorKind.NETWORK


@pytest.mark.asyncio
async def test_chat_with_settings_session_created_without_id() -> None:
    """POST session sem retornar id no JSON -> ChatError PARSE."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"status": "ok"}  # sem name ou id

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with pytest.raises(ChatError) as exc_info:
            await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="user-test",
                jules_api_key="dummy",
            )
        assert exc_info.value.kind == ChatErrorKind.PARSE


@pytest.mark.asyncio
async def test_chat_with_settings_polling_network_blip_e_4xx_continua() -> None:
    """GET activities falha com HTTPError ou 4xx, mas continua ate responder."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"id": "session-123"}

    # 1. Falha de rede (HTTPError)
    # 2. Resposta 404 (Jules ainda processando)
    # 3. JSON invalido
    # 4. Sucesso
    mock_get = AsyncMock()
    resp_404 = MagicMock()
    resp_404.status_code = 404
    resp_404.text = "Not Found"

    resp_bad_json = MagicMock()
    resp_bad_json.status_code = 200
    resp_bad_json.json.side_effect = ValueError("bad json")

    resp_success = MagicMock()
    resp_success.status_code = 200
    resp_success.json.return_value = {
        "activities": [
            {
                "originator": "agent",
                "agentMessaged": {"agentMessage": "Finalmente respondido"},
            }
        ]
    }

    mock_get.side_effect = [
        httpx.HTTPError("blip"),
        resp_404,
        resp_bad_json,
        resp_success,
    ]

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with patch("httpx.AsyncClient.get", mock_get):
            resp = await chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="user-test",
                jules_api_key="dummy",
                poll_timeout_sec=5.0,
                poll_interval_sec=0.01,
            )
            assert resp.content == "Finalmente respondido"
            assert mock_get.call_count == 4


@pytest.mark.asyncio
async def test_chat_with_settings_polling_timeout() -> None:
    """Polling atinge timeout sem receber resposta -> ChatError TIMEOUT."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"id": "session-123"}

    activities_resp = MagicMock()
    activities_resp.status_code = 200
    activities_resp.json.return_value = {"activities": []}  # vazia

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=activities_resp)):
            with pytest.raises(ChatError) as exc_info:
                await chat_with_settings(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                    actor_id="user-test",
                    jules_api_key="dummy",
                    poll_timeout_sec=0.05,
                    poll_interval_sec=0.02,
                )
            assert exc_info.value.kind == ChatErrorKind.TIMEOUT


@pytest.mark.asyncio
async def test_chat_with_settings_audit_exception_handling() -> None:
    """Falha interna ao gravar audit log nao quebra o happy path."""
    session_resp = MagicMock()
    session_resp.status_code = 200
    session_resp.json.return_value = {"id": "session-123"}

    activities_resp = MagicMock()
    activities_resp.status_code = 200
    activities_resp.json.return_value = {
        "activities": [
            {
                "originator": "agent",
                "agentMessaged": {"agentMessage": "Ok"},
            }
        ]
    }

    mock_db = MagicMock(spec=Session)

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=session_resp)):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=activities_resp)):
            with patch("app.services.audit.AuditService.log", side_effect=Exception("DB dead")):
                resp = await chat_with_settings(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                    actor_id="user-test",
                    jules_api_key="dummy",
                    poll_timeout_sec=1.0,
                    poll_interval_sec=0.01,
                    db=mock_db,
                )
                assert resp.content == "Ok"
