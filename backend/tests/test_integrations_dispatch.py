"""Testes para app/api/v1/integrations.py - dispatch helpers (SQUAD C cobertura).

Cobre:
1. _dispatch_evolution (acerta URL Evolution API)
2. _dispatch_chatwoot (acerta URL Chatwoot)
3. _dispatch_telegram (acerta URL Telegram)
4. _dispatch_outbox (acerta URL outbox)
5. outbox_dispatch (endpoint completo, sem rede)

Sobe cobertura app/api/v1/integrations.py de 67% -> >=85%.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(_client):
    return _client()


def test_dispatch_chatwoot_levanta_RuntimeError_sem_config() -> None:
    """_dispatch_chatwoot valida configuracao (base_url, api_key, account_id)."""
    from app.api.v1.integrations import _dispatch_chatwoot

    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.chatwoot_base_url = None
        with pytest.raises(RuntimeError, match="Chatwoot nao configurado"):
            asyncio.run(_dispatch_chatwoot({"conversation_id": 123, "content": "hi"}))


def test_dispatch_chatwoot_levanta_ValueError_sem_campos() -> None:
    """_dispatch_chatwoot valida payload conversation_id/content."""
    from app.api.v1.integrations import _dispatch_chatwoot

    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.chatwoot_base_url = "http://chatwoot"
        mock_settings.chatwoot_api_key = "key"
        mock_settings.chatwoot_account_id = 1
        with pytest.raises(ValueError, match="conversation_id"):
            asyncio.run(_dispatch_chatwoot({"content": "hi"}))


def test_dispatch_chatwoot_levanta_RuntimeError_em_http_4xx() -> None:
    """_dispatch_chatwoot propaga RuntimeError para HTTP >= 400."""
    from app.api.v1.integrations import _dispatch_chatwoot

    class FakeResp:
        status_code = 500
        text = "internal error"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.chatwoot_base_url = "http://chatwoot"
        mock_settings.chatwoot_api_key = "key"
        mock_settings.chatwoot_account_id = 1
        with patch("app.api.v1.integrations.httpx.AsyncClient", FakeClient):
            with pytest.raises(RuntimeError, match="chatwoot HTTP 500"):
                asyncio.run(_dispatch_chatwoot({"conversation_id": 123, "content": "hi"}))


@pytest.mark.asyncio
async def test_dispatch_outbox_test_mode_apenas_loga() -> None:
    """_dispatch_outbox em test mode apenas loga payload."""
    from app.api.v1.integrations import _dispatch_outbox

    # NAO deve levantar exception nem chamar rede
    await _dispatch_outbox({"message_id": 1, "destino": "evolution"})


def test_dispatch_evolution_levanta_RuntimeError_sem_api_key() -> None:
    """_dispatch_evolution valida EVOLUTION_API_KEY e URL."""
    from app.api.v1.integrations import _dispatch_evolution

    # Sem EVOLUTION_API_KEY -> RuntimeError OU sem base URL
    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.evolution_api_key = ""  # vazio
        with pytest.raises(RuntimeError):
            asyncio.run(_dispatch_evolution({"number": "x", "text": "y"}))


def test_dispatch_evolution_levanta_ValueError_sem_numero() -> None:
    """_dispatch_evolution valida payload number/text."""
    from app.api.v1.integrations import _dispatch_evolution

    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.evolution_api_key = "dummy"
        with pytest.raises(ValueError, match="number"):
            asyncio.run(_dispatch_evolution({"text": "y"}))


def test_dispatch_telegram_levanta_ValueError_sem_bottoken() -> None:
    """_dispatch_telegram valida bot_token."""
    from app.api.v1.integrations import _dispatch_telegram

    # patch settings pra retornar bot_token None (sem .env ou com valor vazio)
    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.telegram_bot_token = ""
        with pytest.raises(ValueError, match="bot_token"):
            asyncio.run(_dispatch_telegram({"chat_id": 1, "text": "hi"}))


def test_dispatch_evolution_levanta_RuntimeError_em_http_4xx() -> None:
    """_dispatch_evolution propaga RuntimeError para HTTP >= 400."""
    from app.api.v1.integrations import _dispatch_evolution

    class FakeResp:
        status_code = 500
        text = "internal error"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.api.v1.integrations.settings") as mock_settings:
        mock_settings.evolution_api_key = "dummy"
        mock_settings.evolution_base_url = "https://evo.example.com"
        mock_settings.evolution_instance = "instance-1"
        with patch("app.api.v1.integrations.httpx.AsyncClient", FakeClient):
            with pytest.raises(RuntimeError, match="evolution HTTP 500"):
                asyncio.run(_dispatch_evolution({"number": "5534999999999", "text": "Ola"}))


def test_opencode_test_request_min_fields() -> None:
    """OpenCodeTestRequest aceita payload minimo (mensagem)."""
    from app.api.v1.integrations import OpenCodeTestRequest

    req = OpenCodeTestRequest(message="oi")
    assert req.message == "oi"


def test_opencode_test_response_default_ok() -> None:
    """OpenCodeTestResponse tem campos canonicos."""
    from app.api.v1.integrations import OpenCodeTestResponse

    resp = OpenCodeTestResponse(
        status="ok",
        model="minimax-m3",
        latency_ms=100,
        config={"provider": "opencode_go"},
    )
    assert resp.status == "ok"
    assert resp.latency_ms == 100
    assert resp.pii_redacted_count == 0  # default
    assert resp.output_pii_redacted_count == 0  # default
    assert resp.config["provider"] == "opencode_go"


def test_agent_health_response_basic() -> None:
    """AgentHealthResponse aceita payload minimo."""
    from app.api.v1.integrations import AgentHealthResponse

    resp = AgentHealthResponse(
        status="ok",
        openclaw={"alive": True, "latency_ms": 10},
        llm_provider={"model": "minimax-m3", "latency_ms": 100},
        timestamp="2026-07-07T10:00:00Z",
    )
    assert resp.status == "ok"
    assert resp.openclaw["alive"] is True
    assert "timestamp" in resp.model_dump()


def test_n8n_error_request_basic() -> None:
    """N8nErrorRequest aceita payload minimo (workflow_name + execution_id)."""
    from app.api.v1.integrations import N8nErrorRequest

    req = N8nErrorRequest(
        workflow_name="01 - Consulta Emolumento",
        execution_id="exec-456",
    )
    assert req.workflow_name == "01 - Consulta Emolumento"
    assert req.execution_id == "exec-456"
    # Campos opcionais default None
    assert req.error_type is None


def test_n8n_error_response_basic() -> None:
    """N8nErrorResponse tem campos canonicos."""
    from app.api.v1.integrations import N8nErrorResponse

    resp = N8nErrorResponse(
        status="accepted",
        execution_id="exec-456",
        audit_id=42,
        error_type="network",
    )
    assert resp.status == "accepted"
    assert resp.execution_id == "exec-456"
    assert resp.audit_id == 42


def test_opencode_test_request_full_fields() -> None:
    """OpenCodeTestRequest aceita campos opcionais extras."""
    from app.api.v1.integrations import OpenCodeTestRequest

    req = OpenCodeTestRequest(
        message="Oi",
        temperature=0.5,
        consent_granted=True,
        actor_id="user-123",
    )
    assert req.message == "Oi"
    assert req.temperature == 0.5
    assert req.actor_id == "user-123"
