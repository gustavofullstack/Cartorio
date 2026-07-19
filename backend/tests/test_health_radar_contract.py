"""Contrato do radar resumido: degradacao nunca pode virar falso ``online``."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.v1 import router as router_module


def _healthy_db_connect() -> MagicMock:
    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    return connect


def _healthy_redis() -> MagicMock:
    client = MagicMock()
    client.ping.return_value = True
    return client


@pytest.mark.asyncio
async def test_radar_marks_unexpected_http_response_as_degraded() -> None:
    """HTTP recebido, mas fora do contrato, nao e disponibilidade comprovada."""
    response = MagicMock(status_code=503)
    with (
        patch("app.db.engine.connect", _healthy_db_connect()),
        patch("app.api.v1.router.redis.from_url", return_value=_healthy_redis()),
        patch("app.api.v1.router.httpx.AsyncClient.get", new=AsyncMock(return_value=response)),
    ):
        result = await router_module.health_radar()

    assert result["status"] == "yellow"
    assert result["services"]["database"] == "online"
    assert result["services"]["redis"] == "online"
    assert result["services"]["supabase"] == "degraded"


@pytest.mark.asyncio
async def test_radar_marks_transport_failure_as_offline_without_db_fallback() -> None:
    """Postgres local saudavel nao pode ocultar falha para Supabase remoto."""
    with (
        patch("app.db.engine.connect", _healthy_db_connect()),
        patch("app.api.v1.router.redis.from_url", return_value=_healthy_redis()),
        patch(
            "app.api.v1.router.httpx.AsyncClient.get",
            new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
        ),
    ):
        result = await router_module.health_radar()

    assert result["status"] == "yellow"
    assert result["services"]["database"] == "online"
    assert result["services"]["supabase"] == "offline"


@pytest.mark.asyncio
async def test_radar_exposes_optional_unconfigured_service_without_red_alert() -> None:
    """Canal opcional ausente fica explicito, mas nao derruba o semaforo global."""
    response = MagicMock(status_code=200)
    with (
        patch("app.db.engine.connect", _healthy_db_connect()),
        patch("app.api.v1.router.redis.from_url", return_value=_healthy_redis()),
        patch("app.api.v1.router.httpx.AsyncClient.get", new=AsyncMock(return_value=response)),
        patch.object(router_module.settings, "chatwoot_base_url", None),
    ):
        result = await router_module.health_radar()

    assert result["status"] == "green"
    assert result["services"]["chatwoot"] == "unconfigured"
