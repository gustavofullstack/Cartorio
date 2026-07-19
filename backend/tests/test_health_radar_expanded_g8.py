"""G8.15.T4 — Tests for /health/radar/expanded redis_queues category.

Cobre:
- scan_count basico (fakeredis)
- scan_count com hard cap
- scan_count com TTL sampling (expiring_soon)
- _check_redis_queues_sync com fakeredis populado (todas as 6 namespaces)
- _check_redis_queues_sync com Redis offline -> status="down" + zero counts
- _check_redis_queues_sync com DLQ DB populada
- _check_redis_queues_sync LGPD-safe (pii_safe_labels=True)
- _check_redis_queues_sync com namespace saturação (exhausted=True, status=warn)
- _check_redis_queues_category via endpoint (E2E do radar)
- pii_safe_labels_verified assertion (5+ chaves canonicas, nenhuma raw CPF)

LGPD: usa fakeredis (sem rede real). Todas as chaves criadas via
RedisKey helper canonico — valida contrato G8.12.T3.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import asyncio
from typing import Any

import fakeredis
import pytest

from app.api.v1.health_radar_expanded import (
    RADAR_DNS_DOMAINS,
    REDIS_SCAN_HARD_CAP,
    REDIS_TTL_SAMPLE_LIMIT,
    _check_redis_queues_category,
    _check_redis_queues_sync,
    _scan_count,
)
from app.core.redis_keys import RedisKey


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fake_redis():
    """fakeredis sync instance (decode_responses=True).

    fakeredis implementa SCAN, TTL, SET NX EX — necessarios para os testes
    abaixo.
    """
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def fake_redis_populated(fake_redis):
    """fakeredis com 6 namespaces ja populados para teste end-to-end.

    Padroes canonicos G8.12.T3 (cartorio:idem:*, etc) + legados
    (idem:*, redlock:*, bot:mute:*) para validar backward-compat do scanner.
    """
    # 1. Idempotency
    fake_redis.set(RedisKey.idempotency("webhook", "abc123"), "1", ex=86400)
    fake_redis.set(RedisKey.idempotency("webhook", "def456"), "1", ex=86400)
    fake_redis.set("idem:legacy1", "1", ex=86400)

    # 2. Rate-limit (canonica + legada) — com TTLs variaveis
    fake_redis.set(RedisKey.rate_limit("api_key", "n8n_main"), "5", ex=60)
    fake_redis.set(RedisKey.rate_limit("ip", "1.2.3.4"), "10", ex=5)  # expiring soon
    fake_redis.set("ratelimit:apikey:hash999", "20", ex=60)
    fake_redis.set("sliding:ip:ip_hash_42", "30", ex=60)

    # 4. Lock (canonico + legado)
    fake_redis.set(RedisKey.lock("emitir_protocolo:42"), "token", ex=30)
    fake_redis.set("redlock:legacy_lock", "token", ex=30)

    # 5. Bot mute (canonico + legado)
    fake_redis.set(RedisKey.bot_mute("telegram", "42"), "1|hitl", ex=28800)
    fake_redis.set("bot:mute:legacy:1", "1|hitl", ex=28800)

    # 6. Session memory
    fake_redis.set(RedisKey.session("telegram", "user_1"), "{}", ex=3600)
    fake_redis.set("cartorio:sess:wa_user_2", "{}", ex=3600)

    return fake_redis


# ============================================================================
# Unit: _scan_count
# ============================================================================


def test_scan_count_returns_zero_for_empty_namespace(fake_redis):
    """Namespace vazio retorna count=0."""
    count, soon = _scan_count(fake_redis, "cartorio:idem:*", sample_ttls=10)
    assert count == 0
    assert soon == 0


def test_scan_count_handles_multiple_patterns(fake_redis):
    """3 chaves canonicas + 2 legadas = count 5."""
    fake_redis.set(RedisKey.idempotency("webhook", "a"), "1", ex=60)
    fake_redis.set(RedisKey.idempotency("webhook", "b"), "1", ex=60)
    fake_redis.set(RedisKey.idempotency("post", "c"), "1", ex=60)
    fake_redis.set("idem:legacy1", "1", ex=60)
    fake_redis.set("idempotency:legacy2", "1", ex=60)

    count, _ = _scan_count(fake_redis, "cartorio:idem:*", sample_ttls=10)
    assert count == 3
    count, _ = _scan_count(fake_redis, "idem:*", sample_ttls=10)
    assert count == 1
    count, _ = _scan_count(fake_redis, "idempotency:*", sample_ttls=10)
    assert count == 1


def test_scan_count_respects_hard_cap(fake_redis):
    """Hard cap=2 + 5 chaves -> retorna 2 (cap respeitado)."""
    for i in range(5):
        fake_redis.set(RedisKey.idempotency("webhook", f"k{i}"), "1", ex=60)

    count, _ = _scan_count(fake_redis, "cartorio:idem:*", hard_cap=2)
    # Note: scan retorna ate 2 incrementado; loop para quando > hard_cap
    # count pode ser hard_cap+1 (overflow sinalizado) ou <= hard_cap.
    assert count <= 3
    assert count >= 2


def test_scan_count_samples_ttls_for_expiring_soon(fake_redis):
    """TTL=5s -> conta como 'expiring soon'; TTL=60s -> nao conta."""
    fake_redis.set("cartorio:rate_limit:ip:fast", "1", ex=5)
    fake_redis.set("cartorio:rate_limit:ip:slow", "1", ex=60)

    count, soon = _scan_count(
        fake_redis,
        "cartorio:rate_limit:ip:*",
        sample_ttls=10,
        expiring_soon_sec=10,
    )
    assert count == 2
    # Pelo menos 1 (a chave com TTL=5) deve estar no bucket soon
    assert soon >= 1


def test_scan_count_handles_redis_offline():
    """Redis offline (mock) -> retorna (0, 0) sem exception."""
    from unittest.mock import MagicMock

    broken = MagicMock()
    broken.scan.side_effect = ConnectionError("redis offline")

    count, soon = _scan_count(broken, "cartorio:idem:*", sample_ttls=10)
    assert count == 0
    assert soon == 0


# ============================================================================
# Unit: _check_redis_queues_sync
# ============================================================================


def test_check_redis_queues_with_fakeredis_populated(fake_redis_populated, monkeypatch):
    """Snapshot completo de 6 namespaces via fakeredis populado."""
    # Força redis.from_url -> fakeredis e SessionLocal OK
    import redis as redis_sync

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: fake_redis_populated)

    result = _check_redis_queues_sync("redis://fake:6379/0", scan_hard_cap=1000, ttl_sample=64)

    assert result["pii_safe_labels"] is True
    assert result["status"] == "up"
    queues = result["queues"]

    # 1. Idempotency: 3 canonicas + 1 legacy
    assert queues["idempotency_keys_pending"]["count"] == 3
    assert queues["idempotency_keys_pending"]["exhausted"] is False

    # 2. Rate-limit: 4 chaves (2 canonicas + 1 ratelimit + 1 sliding)
    assert queues["rate_limit_buckets_active"]["count"] == 4
    assert queues["rate_limit_buckets_active"]["expiring_soon"] >= 1  # TTL=5s

    # 3. DLQ: source=db_outbox_message (mas 0 msgs no DB)
    assert queues["dlq_messages_pending"]["source"] == "db_outbox_message"
    assert queues["dlq_messages_pending"]["count"] == 0

    # 4. Lock: 2 chaves (1 canonica + 1 legacy)
    assert queues["cartorio_lock_active"]["count"] == 2

    # 5. Bot mute: 2 chaves (1 canonica + 1 legacy)
    assert queues["cartorio_bot_mute_active"]["count"] == 2

    # 6. Session memory: 2 chaves
    assert queues["cartorio_session_memory"]["count"] == 2

    assert "6 namespaces scanned" in result["detail"]


def test_check_redis_queues_status_down_when_redis_offline(monkeypatch):
    """Redis offline -> status=down + queues com count=0."""
    import redis as redis_sync
    from unittest.mock import MagicMock

    broken_client = MagicMock()
    broken_client.ping.side_effect = ConnectionError("boom")

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: broken_client)

    result = _check_redis_queues_sync("redis://fake:6379/0")
    assert result["status"] == "down"
    assert "redis offline" in result["detail"]
    assert result["pii_safe_labels"] is True
    # Todas as queues reportam 0 (early-return path)
    for key, q in result["queues"].items():
        assert q["count"] == 0, f"{key} deveria ter count=0 em Redis offline"


def test_check_redis_queues_status_warn_on_saturation(monkeypatch):
    """1 namespace saturado (count > hard_cap) -> status=warn."""
    fake = fakeredis.FakeRedis(decode_responses=True)

    # Popula alem do cap
    for i in range(150):
        fake.set(RedisKey.idempotency("webhook", f"key{i}"), "1", ex=86400)

    import redis as redis_sync

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: fake)

    # scan_hard_cap=100 -> 150 chaves excedem -> exhausted=True + status=warn
    result = _check_redis_queues_sync("redis://fake:6379/0", scan_hard_cap=100, ttl_sample=10)
    assert result["status"] == "warn"
    assert "cap=100" in result["detail"] or "saturacao" in result["detail"]
    assert result["pii_safe_labels"] is True


def test_check_redis_queues_lgpd_safe_labels(fake_redis_populated, monkeypatch):
    """Todas as chaves usadas sao LGPD-safe (pii_safe_labels=True + canonicas).

    Verifica tambem que os IDs usados nao contem CPF/CNPJ raw.
    """
    import redis as redis_sync

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: fake_redis_populated)

    result = _check_redis_queues_sync("redis://fake:6379/0")

    # Assertions obrigatorias
    assert result["pii_safe_labels"] is True

    # Verifica que cada chave canonica no fakeredis eh LGPD-safe
    from app.core.redis_keys import looks_like_raw_pii

    for key in fake_redis_populated.keys():
        # Chaves canonicas bem formadas NAO devem conter raw CPF/CNPJ
        assert not looks_like_raw_pii(key), f"PII raw em chave: {key}"


def test_check_redis_queues_dlq_from_db(fake_redis, monkeypatch):
    """DLQ pending vem do DB outbox_message (NAO de Redis LIST)."""
    from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus

    # Cria 3 mensagens pending no DB
    from app.db import SessionLocal

    with SessionLocal() as session:
        for i in range(3):
            session.add(
                OutboxMessage(
                    queue=OutboxQueue.EVOLUTION,
                    payload={"i": i},
                    status=OutboxStatus.PENDING,
                    attempts=0,
                )
            )
        session.commit()

    import redis as redis_sync

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: fake_redis)

    result = _check_redis_queues_sync("redis://fake:6379/0")
    assert result["queues"]["dlq_messages_pending"]["source"] == "db_outbox_message"
    assert result["queues"]["dlq_messages_pending"]["count"] >= 3


# ============================================================================
# Async / endpoint integration
# ============================================================================


def test_check_redis_queues_category_handles_redis_failure(monkeypatch):
    """_check_redis_queues_category lida com redis offline via fail-open."""
    import redis as redis_sync
    from unittest.mock import MagicMock

    broken = MagicMock()
    broken.ping.side_effect = ConnectionError("offline")

    monkeypatch.setattr(redis_sync, "from_url", lambda *a, **kw: broken)

    result = asyncio.run(_check_redis_queues_category())
    assert "redis_queues" in result
    payload = result["redis_queues"]
    assert payload["status"] == "down"
    assert payload["pii_safe_labels"] is True


def test_check_redis_queues_category_exception_path(monkeypatch):
    """Exception inesperada em _check_redis_queues_sync -> retorna warn."""
    from app.api.v1 import health_radar_expanded as mod

    def _boom(*a, **kw) -> dict[str, Any]:
        raise RuntimeError("simulated catastrophic")

    monkeypatch.setattr(mod, "_check_redis_queues_sync", _boom)

    result = asyncio.run(_check_redis_queues_category())
    payload = result["redis_queues"]
    assert payload["status"] == "warn"
    assert "RuntimeError" in payload["detail"]


def test_endpoint_includes_redis_queues_category():
    """GET /health/radar/expanded retorna categoria redis_queues."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        # Patch TODAS as categorias (mesmo padrao dos testes existentes)
        from unittest.mock import AsyncMock, patch

        empty_coro = AsyncMock(return_value={})
        with (
            patch(
                "app.api.v1.health_radar_expanded._check_health_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_dns_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_traefik_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_ssh_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_disk_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_mcp_category",
                side_effect=empty_coro,
            ),
            patch(
                "app.api.v1.health_radar_expanded._check_openclaw_category",
                side_effect=empty_coro,
            ),
        ):
            resp = c.get("/api/v1/health/radar/expanded")

    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    # redis_queues deve existir (mesmo que vazio no mock)
    assert "redis_queues" in data["categories"]
    meta = data["metadata"]
    assert meta["version"] == "0.6.1"
    assert meta["redis_scan_hard_cap"] == REDIS_SCAN_HARD_CAP
    assert meta["redis_ttl_sample_limit"] == REDIS_TTL_SAMPLE_LIMIT
    assert meta["domain_count_dns"] == len(RADAR_DNS_DOMAINS)


def test_redis_queues_5_categories_tracked():
    """Smoke test: exatamente 6 chaves de queue no payload."""
    # Documenta o contrato: 6 categorias (idempotency, rate_limit, dlq,
    # lock, bot_mute, session) — task pediu 5+, garantimos 6.
    fake = fakeredis.FakeRedis(decode_responses=True)
    fake.set(RedisKey.idempotency("webhook", "a"), "1", ex=60)
    fake.set(RedisKey.rate_limit("ip", "1.1.1.1"), "1", ex=60)
    fake.set(RedisKey.lock("redlock_x"), "t", ex=30)
    fake.set(RedisKey.bot_mute("telegram", "1"), "1|hitl", ex=3600)
    fake.set(RedisKey.session("telegram", "u1"), "{}", ex=3600)
    # DLQ vem do DB, mas existe o slot

    import redis as redis_sync
    from unittest.mock import patch

    from app.api.v1 import health_radar_expanded as mod

    captured: dict[str, Any] = {}

    real_fn = mod._check_redis_queues_sync

    def _capture(url, **kw):
        captured.update(real_fn(url, **kw))
        return captured

    with patch.object(redis_sync, "from_url", lambda *a, **kw: fake):
        with patch.object(mod, "_check_redis_queues_sync", _capture):
            result = asyncio.run(_check_redis_queues_category())

    assert "redis_queues" in result
    payload = result["redis_queues"]
    queue_keys = list(payload["queues"].keys())
    assert len(queue_keys) == 6, f"expected 6 queue categories, got {queue_keys}"
    expected_keys = {
        "idempotency_keys_pending",
        "rate_limit_buckets_active",
        "dlq_messages_pending",
        "cartorio_lock_active",
        "cartorio_bot_mute_active",
        "cartorio_session_memory",
    }
    assert set(queue_keys) == expected_keys
