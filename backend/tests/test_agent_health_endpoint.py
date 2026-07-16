"""Testes para app/api/v1/integrations.py - agent_health endpoint (cobertura).

Cobre:
1. agent_health quando openclaw UP + LLM UP -> status=ok
2. agent_health quando openclaw DOWN + LLM UP -> status=degraded
3. agent_health quando ambos DOWN -> status=down
4. agent_health quando API key ausente

Sobe cobertura integrations.py 76% -> >=85%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.v1.integrations import agent_health


def _make_fake_client(status_code: int, version: str | None = None) -> MagicMock:
    """Cria MagicMock que se comporta como httpx.AsyncClient."""
    fake = MagicMock()

    # __aenter__ e __aexit__ para async context manager
    fake.__aenter__ = AsyncMock(return_value=fake)
    fake.__aexit__ = AsyncMock(return_value=None)

    # get() retorna FakeResp
    fake_resp = MagicMock()
    fake_resp.status_code = status_code
    if version:
        fake_resp.headers = httpx.Headers({"x-openclaw-version": version})
    else:
        fake_resp.headers = httpx.Headers({})
    fake.get = AsyncMock(return_value=fake_resp)
    return fake


@pytest.mark.asyncio
async def test_agent_health_status_ok_quando_openclaw_e_llm_up() -> None:
    """agent_health retorna status='ok' quando openclaw=200 e LLM=200."""

    def factory(*args, **kwargs) -> MagicMock:
        # 1a chamada: openclaw (200 + version)
        # 2a chamada: LLM (200)
        # Distingue pelo URL contido em kwargs
        return _make_fake_client(200, version="1.2.3")

    with patch("app.api.v1.integrations.httpx.AsyncClient", factory):
        with patch("app.api.v1.integrations.settings") as mock_settings:
            mock_settings.openclaw_base_url = "https://claw.example.com"
            mock_settings.opencode_go_api_key = "k"
            mock_settings.opencode_go_base_url = "https://llm.example.com"
            mock_settings.opencode_go_model = "test-model"
            mock_settings.llm_default_provider = "opencode_go"
            result = await agent_health()

    assert result.status == "ok"
    assert result.openclaw["alive"] is True
    assert result.llm_provider["reachable"] is True


@pytest.mark.asyncio
async def test_agent_health_status_degraded_quando_apenas_openclaw_up() -> None:
    """agent_health retorna status='degraded' quando so openclaw=200."""

    call_count = [0]

    def factory(*args, **kwargs) -> MagicMock:
        call_count[0] += 1
        if call_count[0] == 1:
            return _make_fake_client(200)  # openclaw UP
        return _make_fake_client(500)  # LLM 500

    with patch("app.api.v1.integrations.httpx.AsyncClient", factory):
        with patch("app.api.v1.integrations.settings") as mock_settings:
            mock_settings.openclaw_base_url = "https://claw.example.com"
            mock_settings.opencode_go_api_key = "k"
            mock_settings.opencode_go_base_url = "https://llm.example.com"
            mock_settings.opencode_go_model = "test-model"
            mock_settings.llm_default_provider = "opencode_go"
            result = await agent_health()

    # 200 + 500: openclaw alive, LLM NOT reachable
    # 500 NAO esta em (200, 401, 403), entao reachable=False
    assert result.status == "degraded"
    assert result.openclaw["alive"] is True
    assert result.llm_provider["reachable"] is False


@pytest.mark.asyncio
async def test_agent_health_status_down_quando_ambos_down() -> None:
    """agent_health retorna status='down' quando ambos DOWN."""
    call_count = [0]

    def factory(*args, **kwargs) -> MagicMock:
        call_count[0] += 1
        return _make_fake_client(500)

    with patch("app.api.v1.integrations.httpx.AsyncClient", factory):
        with patch("app.api.v1.integrations.settings") as mock_settings:
            mock_settings.openclaw_base_url = "https://claw.example.com"
            mock_settings.opencode_go_api_key = "k"
            mock_settings.opencode_go_base_url = "https://llm.example.com"
            mock_settings.opencode_go_model = "test-model"
            mock_settings.llm_default_provider = "opencode_go"
            result = await agent_health()

    assert result.status == "down"
    assert result.openclaw["alive"] is False
    assert result.llm_provider["reachable"] is False


@pytest.mark.asyncio
async def test_agent_health_status_down_quando_api_key_ausente() -> None:
    """agent_health retorna status='down' quando OPENCODE_GO_API_KEY nao configurado."""
    call_count = [0]

    def factory(*args, **kwargs) -> MagicMock:
        call_count[0] += 1
        return _make_fake_client(500)

    with patch("app.api.v1.integrations.httpx.AsyncClient", factory):
        with patch("app.api.v1.integrations.settings") as mock_settings:
            mock_settings.openclaw_base_url = "https://claw.example.com"
            mock_settings.opencode_go_api_key = ""  # SEM API key
            mock_settings.opencode_go_base_url = "https://llm.example.com"
            mock_settings.opencode_go_model = "test-model"
            mock_settings.llm_default_provider = "opencode_go"
            result = await agent_health()

    assert result.status == "down"
    # Comportamento: opencode_go_api_key falsy → else branch
    assert result.llm_provider["reachable"] is False


@pytest.mark.asyncio
async def test_agent_health_trata_request_error_em_openclaw() -> None:
    """agent_health captura RequestError do openclaw e marca como nao-alive."""

    def factory(*args, **kwargs) -> MagicMock:
        fake = MagicMock()
        fake.__aenter__ = AsyncMock(return_value=fake)
        fake.__aexit__ = AsyncMock(return_value=None)
        # 1a chamada (openclaw) raises
        fake.get = AsyncMock(side_effect=httpx.ConnectError("claw down"))
        return fake

    with patch("app.api.v1.integrations.httpx.AsyncClient", factory):
        with patch("app.api.v1.integrations.settings") as mock_settings:
            mock_settings.openclaw_base_url = "https://claw.example.com"
            mock_settings.opencode_go_api_key = "k"
            mock_settings.opencode_go_base_url = "https://llm.example.com"
            mock_settings.opencode_go_model = "test-model"
            mock_settings.llm_default_provider = "opencode_go"
            result = await agent_health()

    # openclaw down (raised) + LLM: depende de como a 2a chamada (LLM) lida
    # O LLM get tb vai raise (mesmo side_effect), entao LLM cai no except
    assert result.status == "down"  # ambos down
    assert result.openclaw["alive"] is False
    assert "ConnectError" in (result.openclaw.get("error") or "")
