"""Testes do rate limit por API key (3 tiers)."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "test-key-12345")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402

from app.services.rate_limit_by_key import (  # noqa: E402
    RateLimitByKeyMiddleware,
    TIER_POLICIES,
    _hash_api_key,
    identify_tier,
)


# ============================================================================
# identify_tier
# ============================================================================


def test_identify_tier_n8n_prefix() -> None:
    assert identify_tier("n8n-abc123") == "n8n"


def test_identify_tier_n8n_long_key() -> None:
    long_key = "x" * 65
    assert identify_tier(long_key) == "n8n"


def test_identify_tier_dpo_prefix() -> None:
    assert identify_tier("dpo-123") == "dpo"
    assert identify_tier("escrevente-456") == "dpo"
    assert identify_tier("admin-789") == "dpo"


def test_identify_tier_padrao_sem_prefixo() -> None:
    assert identify_tier("random-key") == "padrao"


def test_identify_tier_none_e_padrao() -> None:
    assert identify_tier(None) == "padrao"


def test_identify_tier_empty_string_e_padrao() -> None:
    assert identify_tier("") == "padrao"


# ============================================================================
# _hash_api_key
# ============================================================================


def test_hash_api_key_deterministico() -> None:
    assert _hash_api_key("test") == _hash_api_key("test")


def test_hash_api_key_diferentes_keys() -> None:
    assert _hash_api_key("a") != _hash_api_key("b")


def test_hash_api_key_tamanho_fixo() -> None:
    assert len(_hash_api_key("qualquer-coisa")) == 32


# ============================================================================
# TIER_POLICIES
# ============================================================================


def test_n8n_tem_limite_mais_alto() -> None:
    assert TIER_POLICIES["n8n"].per_minute > TIER_POLICIES["dpo"].per_minute


def test_dpo_tem_limite_maior_que_padrao() -> None:
    assert TIER_POLICIES["dpo"].per_minute > TIER_POLICIES["padrao"].per_minute


def test_padrao_fail_secure_limite_baixo() -> None:
    assert TIER_POLICIES["padrao"].per_minute <= 30


# ============================================================================
# RateLimitByKeyMiddleware (com mock Redis)
# ============================================================================


@pytest.fixture
def mock_redis_client():
    """Mock de redis.asyncio.from_url que retorna cliente com pipeline."""
    client = MagicMock()
    pipeline = MagicMock()

    # Default: incr retorna 1 (allowed)
    incr_mock = AsyncMock(return_value=1)
    expire_mock = AsyncMock(return_value=True)
    pipe_instance = MagicMock()
    pipe_instance.incr = incr_mock
    pipe_instance.expire = expire_mock
    pipe_instance.execute = AsyncMock(return_value=[1, True])
    pipeline.return_value = pipe_instance

    client.pipeline = MagicMock(return_value=pipe_instance)
    client.ping = AsyncMock(return_value=True)

    return client


@pytest.mark.asyncio
async def test_middleware_allow_quando_primeira_request(mock_redis_client) -> None:
    """Primeira request: allowed."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {"x-api-key": "n8n-test"}
    request.url.path = "/api/v1/test"

    with patch("app.services.rate_limit_by_key.redis_async.from_url", return_value=mock_redis_client):
        # Bypass call_next real
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        response = await mw.dispatch(request, call_next)

    assert response.headers.get("X-RateLimit-Limit") == "600"  # n8n tier
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_429_quando_excede_limite(mock_redis_client) -> None:
    """Request que excede limite: 429."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {"x-api-key": "test"}
    request.url.path = "/api/v1/test"

    # Mock incr retornando valor acima do limite
    pipe_instance = mock_redis_client.pipeline.return_value
    pipe_instance.execute = AsyncMock(return_value=[61, True])  # 61 > 60 (dpo tier)

    with patch("app.services.rate_limit_by_key.redis_async.from_url", return_value=mock_redis_client):
        call_next = AsyncMock()
        response = await mw.dispatch(request, call_next)

    assert response.status_code == 429
    assert b"RATE_LIMITED" in response.body
    assert response.headers.get("Retry-After") is not None
    call_next.assert_not_called()  # nao chama next


@pytest.mark.asyncio
async def test_middleware_fail_open_quando_redis_offline() -> None:
    """Redis offline: fail-open (permite request + log warning)."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {"x-api-key": "test"}
    request.url.path = "/api/v1/test"

    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url",
        side_effect=OSError("connection refused"),
    ):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        await mw.dispatch(request, call_next)

    # Fail-open: passa pro next
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_path_nao_rate_limited_passa_direto(mock_redis_client) -> None:
    """Path fora do paths_prefixes NAO eh rate-limited."""
    mw = RateLimitByKeyMiddleware(
        app=MagicMock(), redis_url="redis://fake", paths_prefixes=("/api/v1/",)
    )

    request = MagicMock()
    request.headers = {"x-api-key": "test"}
    request.url.path = "/health"  # nao em /api/v1/

    call_next = AsyncMock(return_value=MagicMock(headers={}))
    response = await mw.dispatch(request, call_next)

    call_next.assert_called_once()
    # Nenhum header de rate limit adicionado
    assert "X-RateLimit-Limit" not in response.headers


@pytest.mark.asyncio
async def test_middleware_sem_api_key_usa_ip_como_hash() -> None:
    """Sem X-API-Key: usa IP do cliente (LGPD-safe via hash)."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {
        "x-forwarded-for": "203.0.113.7, 10.0.0.1",  # IP real + proxy
    }
    request.url.path = "/api/v1/test"

    pipe_instance = MagicMock()
    pipe_instance.execute = AsyncMock(return_value=[1, True])
    client = MagicMock()
    client.pipeline = MagicMock(return_value=pipe_instance)
    client.ping = AsyncMock(return_value=True)

    with patch("app.services.rate_limit_by_key.redis_async.from_url", return_value=client):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        response = await mw.dispatch(request, call_next)

    # Tier padrao (30/min) - verifica que eh o limite
    assert response.headers.get("X-RateLimit-Limit") == "30"
    call_next.assert_called_once()
