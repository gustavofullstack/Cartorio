"""Testes do rate limit por API key (3 tiers)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.rate_limit_by_key import (  # noqa: E402
    RateLimitByKeyMiddleware,
    TIER_POLICIES,
    _hash_api_key,
    identify_tier,
)

VALID_KEY = settings.cartorio_api_key


# ============================================================================
# identify_tier (E2.03 H4 - anti-spoofing)
# ============================================================================


def test_identify_tier_key_registrada_e_n8n() -> None:
    """Key valida registrada (settings.cartorio_api_key) -> tier n8n."""
    assert identify_tier(VALID_KEY) == "n8n"


def test_identify_tier_prefixo_n8n_forjado_e_padrao() -> None:
    """Prefixo 'n8n-'/'sk-n8n-' NAO eleva tier (spoofing)."""
    assert identify_tier("n8n-abc123") == "padrao"
    assert identify_tier("sk-n8n-abc123") == "padrao"


def test_identify_tier_prefixo_dpo_forjado_e_padrao() -> None:
    """Prefixo 'dpo-'/'escrevente-'/'admin-' NAO eleva tier (spoofing)."""
    assert identify_tier("dpo-123") == "padrao"
    assert identify_tier("escrevente-456") == "padrao"
    assert identify_tier("admin-789") == "padrao"


def test_identify_tier_string_longa_desconhecida_e_padrao() -> None:
    """String longa (>64) desconhecida NAO eleva tier (spoofing)."""
    assert identify_tier("x" * 65) == "padrao"
    assert identify_tier("f" * 128) == "padrao"


def test_identify_tier_quase_valida_e_padrao() -> None:
    """Near-miss da key registrada (1 char diferente/case) -> padrao."""
    assert identify_tier(VALID_KEY[:-1] + "b") == "padrao"
    assert identify_tier(VALID_KEY.upper()) == "padrao"
    assert identify_tier(VALID_KEY + "a") == "padrao"
    assert identify_tier(VALID_KEY[:-1]) == "padrao"


def test_identify_tier_malformada_unicode_e_padrao() -> None:
    """Key malformada (nao-ASCII) nao quebra compare_digest."""
    assert identify_tier("n8n-çãö🙂") == "padrao"


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
    # NOTE: pipeline.incr/expire sao sincronos (apenas enfileiram comando)
    # Nao sao AsyncMock (evita RuntimeWarning de coroutine nao awaitada)
    pipe_instance = MagicMock()
    pipe_instance.incr.return_value = None
    pipe_instance.expire.return_value = None
    pipe_instance.execute = AsyncMock(return_value=[1, True])
    pipeline.return_value = pipe_instance

    client.pipeline = MagicMock(return_value=pipe_instance)
    client.ping = AsyncMock(return_value=True)

    return client


@pytest.mark.asyncio
async def test_telegram_webhook_bypassa_rate_limit_por_ter_secret_proprio() -> None:
    """Webhook Telegram nao deve compartilhar o bucket de IP/API key."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {}
    request.url.path = "/api/v1/telegram/webhook"
    response = MagicMock(headers={})
    call_next = AsyncMock(return_value=response)

    with patch.object(mw, "_get_client", new=AsyncMock(side_effect=AssertionError)):
        result = await mw.dispatch(request, call_next)

    assert result is response
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_middleware_allow_quando_primeira_request(mock_redis_client) -> None:
    """Primeira request com key registrada: allowed (tier n8n)."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {"x-api-key": VALID_KEY}
    request.url.path = "/api/v1/test"

    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url", return_value=mock_redis_client
    ):
        # Bypass call_next real
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        response = await mw.dispatch(request, call_next)

    assert response.headers.get("X-RateLimit-Limit") == "600"  # n8n tier
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_key_com_prefixo_n8n_forjado_cai_em_padrao(mock_redis_client) -> None:
    """E2.03 H4: key desconhecida com prefixo 'n8n-' NAO ganha 600/min."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")

    request = MagicMock()
    request.headers = {"x-api-key": "n8n-test"}
    request.url.path = "/api/v1/test"

    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url", return_value=mock_redis_client
    ):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        response = await mw.dispatch(request, call_next)

    assert response.headers.get("X-RateLimit-Limit") == "30"  # padrao, nao n8n
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
    pipe_instance.execute = AsyncMock(return_value=[61, True])  # 61 > 30 (tier padrao)

    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url", return_value=mock_redis_client
    ):
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
