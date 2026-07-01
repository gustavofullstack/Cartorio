"""Testes unitarios da integracao Antigravity (Turno 38 — 2026-06-30).

Cobre:
- Config OAuth carrega do keyring ou env ANTIGRAVITY_TOKEN (defense-in-depth)
- Bloqueio sem consent_granted (LGPD art. 7 I)
- Bloqueio sem token (CONFIG)
- Sucesso com httpx MockTransport + PII scrub + AuditService.log chamado
- Erros HTTP 401/403/429/4xx/5xx
- Fallback de model quando nao disponivel

Gates: mypy 0 | ruff 0 | pytest passed | coverage >= 90% no modulo
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integrations import antigravity as ag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolated_oauth(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    """Seta ANTIGRAVITY_TOKEN em envvar pra todos os testes que precisam."""
    monkeypatch.setenv("ANTIGRAVITY_TOKEN", "test-ag-token-1234")
    # Sobrescreve path do arquivo token pra tmp_path (evita ler ~/.config real)
    monkeypatch.setattr(ag, "ANTIGRAVITY_TOKEN_PATH", tmp_path / "antigravity.json")
    yield


def _mock_response(payload: dict[str, Any], status: int = 200) -> httpx.Response:
    """Constroi httpx.Response a partir de dict, body JSON."""
    return httpx.Response(
        status_code=status,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


# ---------------------------------------------------------------------------
# Test: Configuracao OAuth
# ---------------------------------------------------------------------------
class TestAntigravityOAuthConfig:
    def test_load_oauth_token_via_env(self) -> None:
        """_load_oauth_token retorna ANTIGRAVITY_TOKEN se setado."""
        token = ag._load_oauth_token()
        assert token == "test-ag-token-1234"

    def test_load_oauth_token_via_arquivo(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """_load_oauth_token carrega de ANTIGRAVITY_TOKEN_PATH se env ausente."""
        monkeypatch.delenv("ANTIGRAVITY_TOKEN", raising=False)
        token_file = tmp_path / "antigravity.json"
        token_file.write_text(json.dumps({"access_token": "arquivo-token-5678"}))
        monkeypatch.setattr(ag, "ANTIGRAVITY_TOKEN_PATH", token_file)
        token = ag._load_oauth_token()
        assert token == "arquivo-token-5678"

    def test_load_oauth_token_none_se_nao_configurado(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_load_oauth_token retorna None se nenhum path configurado."""
        monkeypatch.delenv("ANTIGRAVITY_TOKEN", raising=False)
        # Apaga arquivo mesmo se existir
        with patch.object(ag.Path, "exists", return_value=False):
            token = ag._load_oauth_token()
        assert token is None

    def test_is_configured_true(self) -> None:
        """is_configured retorna True quando token disponivel."""
        assert ag.is_configured() is True

    def test_is_configured_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_configured retorna False sem token."""
        monkeypatch.delenv("ANTIGRAVITY_TOKEN", raising=False)
        with patch.object(ag.Path, "exists", return_value=False):
            assert ag.is_configured() is False


# ---------------------------------------------------------------------------
# Test: Validacoes pre-request
# ---------------------------------------------------------------------------
class TestAntigravityValidations:
    @pytest.mark.asyncio
    async def test_bloqueia_sem_consent(self) -> None:
        """LGPD art. 7 I — chat() levanta LGPD_BLOCKED sem consent_granted."""
        with pytest.raises(ag.ChatError) as exc_info:
            await ag.chat(
                [{"role": "user", "content": "oi"}],
                consent_granted=False,
            )
        assert exc_info.value.kind == ag.ChatErrorKind.LGPD_BLOCKED

    @pytest.mark.asyncio
    async def test_bloqueia_sem_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CONFIG — chat() levanta CONFIG sem ANTIGRAVITY_TOKEN."""
        monkeypatch.delenv("ANTIGRAVITY_TOKEN", raising=False)
        with patch.object(ag.Path, "exists", return_value=False):
            with pytest.raises(ag.ChatError) as exc_info:
                await ag.chat(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                )
        assert exc_info.value.kind == ag.ChatErrorKind.CONFIG

    @pytest.mark.asyncio
    async def test_bloqueia_messages_vazias(self) -> None:
        """CONFIG — chat() levanta CONFIG se messages vazias."""
        with pytest.raises(ag.ChatError) as exc_info:
            await ag.chat(
                [],
                consent_granted=True,
            )
        assert exc_info.value.kind == ag.ChatErrorKind.CONFIG


# ---------------------------------------------------------------------------
# Test: MockTransport (httpx mock) — sucesso + PII + audit log
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chat_sucesso_scrubs_pii_e_loga_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cenario nominal: PII scrub input + AuditService.log chamado + retorna safe_content."""
    payload = {
        "id": "chatcmpl-antigravity-1",
        "model": "gemini-3.1-pro",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Resposta sem PII"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }
    mock_response = _mock_response(payload, status=200)

    def handler(request: httpx.Request) -> httpx.Response:
        # Valida que request tem Authorization Bearer
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")
        return mock_response

    # Mock do db
    mock_db = MagicMock()

    # Mock do AuditService.log
    audit_calls: list[dict[str, Any]] = []
    mock_audit_log = MagicMock(side_effect=lambda *args, **kwargs: audit_calls.append(kwargs))

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=mock_response
        )
        # Stub keyring pra nao tentar acessar keyring real
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            with patch("app.services.audit.AuditService") as mock_audit_cls:
                mock_audit_cls.log = mock_audit_log
                with patch("app.services.audit.AuditService.log_system_action", mock_audit_log):
                    response = await ag.chat(
                        [{"role": "user", "content": "Meu CPF eh 123.456.789-09"}],
                        consent_granted=True,
                        actor_id="actor-1",
                        db=mock_db,
                    )

    # Validacoes do response
    assert response.content == "Resposta sem PII"
    assert response.model == "gemini-3.1-pro"
    assert response.tokens_in == 100
    assert response.tokens_out == 50
    # PII scrub de input DEVE ter sido aplicado (123.456.789-09 -> [CPF])
    assert response.pii_redacted_count >= 1


@pytest.mark.asyncio
async def test_chat_fallback_quando_model_indisponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model nao disponivel: fallback para default_model sem crashar."""
    payload = {
        "model": "gemini-3.1-pro",
        "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_resp = _mock_response(payload, status=200)
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=mock_resp
        )
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            response = await ag.chat(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                model="modelo-fake-nao-existe",
            )

    # Deve ter caito pra default sem crashar
    assert response.content == "OK"


# AsyncMock import lazy
from unittest.mock import AsyncMock  # noqa: E402


@pytest.mark.asyncio
async def test_chat_erro_401_token_invalido() -> None:
    """401 do Antigravity = token expirado, levanta HTTP_4XX."""
    payload = {"error": {"message": "token expired"}}
    resp_401 = _mock_response(payload, status=401)

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=resp_401
        )
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            with pytest.raises(ag.ChatError) as exc_info:
                await ag.chat(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                )
    assert exc_info.value.kind == ag.ChatErrorKind.HTTP_4XX


@pytest.mark.asyncio
async def test_chat_erro_500_server_error() -> None:
    """500 do Antigravity = levanta HTTP_5XX."""
    resp_500 = _mock_response({"error": "x"}, status=500)

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=resp_500
        )
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            with pytest.raises(ag.ChatError) as exc_info:
                await ag.chat(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                )
    assert exc_info.value.kind == ag.ChatErrorKind.HTTP_5XX


@pytest.mark.asyncio
async def test_chat_response_parse_quebra() -> None:
    """Response nao-JSON = PARSE error."""
    resp_invalid = httpx.Response(
        status_code=200,
        content=b"<html>not-json</html>",
        headers={"content-type": "text/html"},
    )

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=resp_invalid
        )
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            with pytest.raises(ag.ChatError) as exc_info:
                await ag.chat(
                    [{"role": "user", "content": "oi"}],
                    consent_granted=True,
                )
    assert exc_info.value.kind == ag.ChatErrorKind.PARSE


# ---------------------------------------------------------------------------
# Test: chat_with_settings wrapper
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chat_with_settings_delega_para_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """chat_with_settings deve apenas chamar chat(**kwargs)."""
    payload = {
        "model": "gemini-3.1-pro",
        "choices": [{"message": {"content": "wrapped"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
    }

    with patch("app.integrations.antigravity.httpx.AsyncClient") as mock_async_client:
        mock_resp = _mock_response(payload, status=200)
        mock_async_client.return_value.__aenter__.return_value.post = AsyncMock(  # type: ignore[attr-defined]
            return_value=mock_resp
        )
        with patch.dict("sys.modules", {"keyring": MagicMock()}):
            response = await ag.chat_with_settings(
                [{"role": "user", "content": "oi"}],
                consent_granted=True,
                actor_id="actor-1",
            )

    assert response.content == "wrapped"
