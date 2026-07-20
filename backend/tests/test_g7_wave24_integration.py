"""G7 Wave 24 — coverage gap fill (rate_limit_by_key / radar / sentry).

Foca branches ainda <90% apos Wave 23:
- rate_limit_by_key: DDoS 429, sliding 429, RedisError mid-pipe, metrics fail
- health_radar_expanded: dns generic exc, wait_closed, health DB/redis fail,
  non-200 upstream, n8n missing URL, coerce non-dict
- sentry: json.dumps fail em before_send + capture_exception com extra

Modified by Gustavo Almeida — G7 Wave 24.
"""

from __future__ import annotations

import asyncio
import json
from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis_async

from app.services.rate_limit_by_key import RateLimitByKeyMiddleware, RateLimitResult
from app.services.sentry import _before_send, capture_exception


# ============================================================================
# rate_limit_by_key — branches miss (85% → ~100%)
# ============================================================================


def _pipe_client(incr_value: int = 1) -> MagicMock:
    """Cliente Redis mock com pipeline.incr/expire/execute."""
    pipe = MagicMock()
    pipe.incr.return_value = None
    pipe.expire.return_value = None
    pipe.execute = AsyncMock(return_value=[incr_value, True])
    client = MagicMock()
    client.pipeline = MagicMock(return_value=pipe)
    client.ping = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_rate_limit_ddos_layer_returns_429() -> None:
    """Camada DDoS (fixed window por IP) bloqueia com RATE_LIMITED_DDOS."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake", ddos_per_minute=100)
    request = MagicMock()
    request.headers = {"x-api-key": "n8n-test", "x-forwarded-for": "203.0.113.9"}
    request.url.path = "/api/v1/test"
    request.client = SimpleNamespace(host="203.0.113.9")

    denied = RateLimitResult(allowed=False, current=101, limit=100, retry_after=42)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=denied)),
        patch(
            "app.services.metrics.store.inc_rate_limit_total",
            MagicMock(),
        ) as metrics_inc,
    ):
        call_next = AsyncMock()
        response = await mw.dispatch(request, call_next)

    assert response.status_code == 429
    assert b"RATE_LIMITED_DDOS" in response.body
    assert response.headers["Retry-After"] == "42"
    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    call_next.assert_not_called()
    metrics_inc.assert_called_with(layer="ddos", tier="none")


@pytest.mark.asyncio
async def test_rate_limit_ddos_metrics_fail_still_429() -> None:
    """Metrics exception no path DDoS nao impede 429 (fail-open metrics)."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-forwarded-for": "198.51.100.1"}
    request.url.path = "/api/v1/test"
    request.client = SimpleNamespace(host="198.51.100.1")

    denied = RateLimitResult(allowed=False, current=200, limit=100, retry_after=10)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=denied)),
        patch(
            "app.services.metrics.store.inc_rate_limit_total",
            side_effect=RuntimeError("metrics down"),
        ),
    ):
        response = await mw.dispatch(request, AsyncMock())

    assert response.status_code == 429
    assert b"RATE_LIMITED_DDOS" in response.body


@pytest.mark.asyncio
async def test_rate_limit_sliding_layer_returns_429() -> None:
    """Camada sliding window bloqueia com RATE_LIMITED_SLIDING."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-api-key": "n8n-ok", "x-forwarded-for": "203.0.113.10"}
    request.url.path = "/api/v1/test"
    request.client = SimpleNamespace(host="203.0.113.10")

    allow = RateLimitResult(allowed=True, current=1, limit=100, retry_after=0)
    denied_sliding = RateLimitResult(allowed=False, current=101, limit=100, retry_after=33)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=allow)),
        patch.object(mw, "_check_sliding_window", new=AsyncMock(return_value=denied_sliding)),
        patch("app.services.metrics.store.inc_rate_limit_total", MagicMock()) as metrics_inc,
    ):
        call_next = AsyncMock()
        response = await mw.dispatch(request, call_next)

    assert response.status_code == 429
    assert b"RATE_LIMITED_SLIDING" in response.body
    assert response.headers["X-RateLimit-Algorithm"] == "sliding-window"
    assert response.headers["Retry-After"] == "33"
    call_next.assert_not_called()
    metrics_inc.assert_called_with(layer="sliding", tier="none")


@pytest.mark.asyncio
async def test_rate_limit_sliding_metrics_fail_still_429() -> None:
    """Metrics exception no path sliding nao impede 429."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.11"}
    request.url.path = "/api/v1/test"
    request.client = SimpleNamespace(host="203.0.113.11")

    allow = RateLimitResult(allowed=True, current=1, limit=100, retry_after=0)
    denied_sliding = RateLimitResult(allowed=False, current=150, limit=100, retry_after=5)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=allow)),
        patch.object(mw, "_check_sliding_window", new=AsyncMock(return_value=denied_sliding)),
        patch(
            "app.services.metrics.store.inc_rate_limit_total",
            side_effect=ImportError("no metrics"),
        ),
    ):
        response = await mw.dispatch(request, AsyncMock())

    assert response.status_code == 429
    assert b"RATE_LIMITED_SLIDING" in response.body


@pytest.mark.asyncio
async def test_rate_limit_tier_metrics_fail_still_429() -> None:
    """Metrics exception no path tier (339-340) nao impede 429."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-api-key": "random-key", "x-forwarded-for": "203.0.113.12"}
    request.url.path = "/api/v1/test"
    request.client = SimpleNamespace(host="203.0.113.12")

    allow = RateLimitResult(allowed=True, current=1, limit=100, retry_after=0)
    tier_denied = RateLimitResult(allowed=False, current=99, limit=30, retry_after=12)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=allow)),
        patch.object(mw, "_check_sliding_window", new=AsyncMock(return_value=allow)),
        patch.object(mw, "_check", new=AsyncMock(return_value=tier_denied)),
        patch(
            "app.services.metrics.store.inc_rate_limit_total",
            side_effect=RuntimeError("metrics boom"),
        ),
    ):
        call_next = AsyncMock()
        response = await mw.dispatch(request, call_next)

    assert response.status_code == 429
    assert b"RATE_LIMITED" in response.body
    assert b"RATE_LIMITED_DDOS" not in response.body
    assert b"RATE_LIMITED_SLIDING" not in response.body
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_check_redis_error_fail_open() -> None:
    """_check: RedisError no pipeline.execute → fail-open (allowed)."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    client = _pipe_client()
    client.pipeline.return_value.execute = AsyncMock(
        side_effect=redis_async.RedisError("broken pipe")
    )
    mw._client = client  # type: ignore[assignment]

    result = await mw._check("abc123hash", "padrao")
    assert result.allowed is True
    assert result.limit == 0


@pytest.mark.asyncio
async def test_rate_limit_ip_ddos_redis_error_fail_open() -> None:
    """_check_ip_ddos: RedisError no pipeline → fail-open."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake", ddos_per_minute=50)
    client = _pipe_client()
    client.pipeline.return_value.execute = AsyncMock(side_effect=redis_async.RedisError("timeout"))
    mw._client = client  # type: ignore[assignment]

    result = await mw._check_ip_ddos("203.0.113.99")
    assert result.allowed is True
    assert result.current == 0


@pytest.mark.asyncio
async def test_rate_limit_client_ip_fallback_to_request_client() -> None:
    """Sem x-forwarded-for: usa request.client.host no path allowed."""
    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-api-key": "n8n-abc"}  # sem XFF
    request.url.path = "/api/v1/health"
    request.client = SimpleNamespace(host="10.0.0.5")

    allow = RateLimitResult(allowed=True, current=1, limit=100, retry_after=0)
    with (
        patch.object(mw, "_check_ip_ddos", new=AsyncMock(return_value=allow)) as ddos,
        patch.object(mw, "_check_sliding_window", new=AsyncMock(return_value=allow)),
        patch.object(mw, "_check", new=AsyncMock(return_value=allow)),
    ):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        await mw.dispatch(request, call_next)
        ddos.assert_awaited_once_with("10.0.0.5")


# ============================================================================
# sentry — branches miss (94% → ~100%)
# ============================================================================


def test_before_send_json_dumps_orig_fails() -> None:
    """json.dumps no event original falha → orig_str='' e segue scrub."""
    event: dict = {"message": "ok sem pii"}
    # object() nao serializa; injeta valor circular-like via patch
    with patch("json.dumps", side_effect=[TypeError("not serializable"), json.dumps(event)]):
        result = _before_send(event, {})
    assert result is not None
    assert result["message"] == "ok sem pii"


def test_before_send_json_dumps_scrubbed_fails() -> None:
    """json.dumps apos scrub falha → scrubbed_str='' (sem crash)."""
    event: dict = {"message": "CPF 123.456.789-00"}
    call_count = {"n": 0}

    def _dumps(obj: object, *args: object, **kwargs: object) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return '{"message":"CPF 123.456.789-00"}'
        raise TypeError("cannot serialize scrubbed")

    with patch("json.dumps", side_effect=_dumps):
        result = _before_send(event, {})
    assert result is not None
    assert "[MASKED:cpf]" in result["message"]


def test_capture_exception_with_extra_sets_scope() -> None:
    """capture_exception com extra chama set_extra com PII scrubbed (linha 150)."""
    with patch("app.services.sentry._init_sentry", return_value=True):
        mock_sentry = MagicMock()
        scope_mock = MagicMock()
        mock_sentry.push_scope.return_value = scope_mock
        scope_mock.__enter__ = MagicMock(return_value=scope_mock)
        scope_mock.__exit__ = MagicMock(return_value=None)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_exception(
                ValueError("boom"),
                extra={"cpf": "123.456.789-00", "note": "safe"},
            )

        assert mock_sentry.capture_exception.called
        assert scope_mock.set_extra.called
        args, _ = scope_mock.set_extra.call_args
        assert args[0] == "context"
        assert "[MASKED:cpf]" in str(args[1])


# ============================================================================
# health_radar_expanded — branches miss (93% → ~100%)
# ============================================================================


def test_dns_check_generic_exception_returns_down() -> None:
    """_check_dns: Exception generica (nao Timeout/FileNotFound) → down."""
    from app.api.v1.health_radar_expanded import _check_dns

    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=RuntimeError("unexpected dig failure"),
    ):
        result = asyncio.run(_check_dns("example.invalid"))
    assert result["status"] == "down"
    assert "RuntimeError" in result["detail"]


def test_socket_check_wait_closed_exception_still_up() -> None:
    """_check_socket: wait_closed lanca Exception → ainda retorna up (open)."""
    from app.api.v1.health_radar_expanded import _check_socket

    writer = MagicMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock(side_effect=RuntimeError("already closed"))

    async def _open(*_a: object, **_k: object) -> tuple[MagicMock, MagicMock]:
        return MagicMock(), writer

    with patch("asyncio.open_connection", side_effect=_open):
        result = asyncio.run(_check_socket("127.0.0.1", 9, timeout=1.0))
    assert result["status"] == "up"
    assert "open" in result["detail"]


def test_check_health_category_db_and_redis_fail() -> None:
    """_check_health_category: DB e Redis falham → down + *_error keys."""
    from app.api.v1.health_radar_expanded import _check_health_category

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with (
        patch("app.api.v1.health_radar_expanded.engine") as mock_engine,
        patch("redis.from_url", side_effect=OSError("redis offline")),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_engine.connect.side_effect = OSError("db offline")
        result = asyncio.run(_check_health_category())

    assert result["database"]["status"] == "down"
    assert "database_error" in result
    assert result["redis"]["status"] == "down"
    assert "redis_error" in result


def test_check_health_category_upstream_non_200_is_degraded() -> None:
    """Resposta HTTP inesperada e alcancavel, mas nao confirma saude."""
    from app.api.v1.health_radar_expanded import _check_health_category

    def _status_for_url(url: str) -> int:
        if "openclaw" in url or "agent" in url:
            return 503
        if "evolution" in url or "evo" in url or url.rstrip("/").endswith(":8080"):
            return 502
        return 500

    async def _get(url: str, *args: object, **kwargs: object) -> MagicMock:
        resp = MagicMock()
        resp.status_code = _status_for_url(url)
        return resp

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=_get)

    mock_conn = MagicMock()
    mock_conn.execute = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=None)

    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with (
        patch("app.api.v1.health_radar_expanded.engine", mock_engine),
        patch("redis.from_url", return_value=mock_redis),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("app.api.v1.health_radar_expanded.settings") as settings,
    ):
        settings.redis_url = "redis://localhost"
        settings.openclaw_base_url = "http://openclaw.local"
        settings.evolution_base_url = "http://evolution.local"
        settings.chatwoot_base_url = "http://chatwoot.local"
        settings.supabase_url = "http://supabase.local"
        settings.n8n_base_url = "http://n8n.local"
        result = asyncio.run(_check_health_category())

    assert result["openclaw"]["status"] == "warn"
    assert "HTTP 503" in result["openclaw"]["detail"]
    assert result["evolution"]["status"] == "warn"
    assert result["chatwoot"]["status"] == "warn"
    assert result["supabase"]["status"] == "warn"
    assert result["n8n"]["status"] == "warn"


def test_check_health_category_n8n_missing_url() -> None:
    """n8n com base_url vazio aciona branch missing URL config."""
    from app.api.v1.health_radar_expanded import _check_health_category

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_conn = MagicMock()
    mock_conn.execute = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with (
        patch("app.api.v1.health_radar_expanded.engine", mock_engine),
        patch("redis.from_url", return_value=mock_redis),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("app.api.v1.health_radar_expanded.settings") as settings,
    ):
        settings.redis_url = "redis://localhost"
        settings.openclaw_base_url = "http://openclaw.local"
        settings.evolution_base_url = "http://evolution.local"
        settings.chatwoot_base_url = "http://chatwoot.local"
        settings.supabase_url = "http://supabase.local"
        settings.n8n_base_url = ""
        result = asyncio.run(_check_health_category())

    assert result["n8n"]["status"] == "warn"
    assert "missing URL config" in result["n8n"]["detail"]


@pytest.mark.asyncio
async def test_health_radar_expanded_coerce_non_dict_fallback() -> None:
    """gather retorna tipo inesperado (str) → _coerce usa fallback {}."""
    from app.api.v1.health_radar_expanded import health_radar_expanded

    with (
        patch(
            "app.api.v1.health_radar_expanded._check_health_category",
            new=AsyncMock(return_value="not-a-dict"),  # type: ignore[arg-type]
        ),
        patch(
            "app.api.v1.health_radar_expanded._check_dns_category",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.api.v1.health_radar_expanded._check_traefik_category",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.api.v1.health_radar_expanded._check_ssh_category",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.api.v1.health_radar_expanded._check_disk_category",
            new=AsyncMock(return_value={}),
        ),
    ):
        out = await health_radar_expanded()

    assert out["categories"]["health"] == {}
    assert out["status"] in ("green", "yellow", "red")
    assert out["metadata"]["version"] == "0.6.1"


def test_disk_check_warn_when_usage_over_85() -> None:
    """_check_disk: percent_used > 85 → warn."""
    from app.api.v1.health_radar_expanded import _check_disk

    Usage = namedtuple("Usage", ["total", "used", "free"])
    # 90% used: total=1000, used=900, free=100
    with patch("shutil.disk_usage", return_value=Usage(total=1000, used=900, free=100)):
        result = _check_disk("/var/lib/docker/volumes")
    assert result["status"] == "warn"
    assert "used" in result["detail"]
