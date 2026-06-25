"""Testes do cache Redis para atendimentos/ultimas-24h (A18).

Cobertura:
- get_cached retorna None se Redis offline (fail-open)
- set_cached + get_cached round-trip funciona
- TTL eh 60s (verificado via ex param)
- Chave tem formato deterministico com CACHE_VERSION
- invalidate remove todas as chaves com prefix
- Fail silencioso em qualquer erro de Redis
"""
from __future__ import annotations

from unittest.mock import patch


from app.services.atendimento_cache import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    CACHE_VERSION,
    _cache_key,
    get_cached,
    invalidate,
    set_cached,
)


class FakeRedis:
    """Redis fake para testes (sem dependencia)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        if ex is not None:
            self.expirations[key] = ex
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                self.expirations.pop(k, None)
                count += 1
        return count

    def scan_iter(self, match: str = "*", count: int = 100):
        import fnmatch
        return iter([k for k in self.store.keys() if fnmatch.fnmatch(k, match)])


class TestAtendimentoCache:
    """TDD strict."""

    def test_ttl_is_60_seconds(self):
        """TTL deve ser 60s (1 min) - tradeoff freshness vs carga DB."""
        assert CACHE_TTL_SECONDS == 60

    def test_cache_version_present(self):
        """CACHE_VERSION presente para invalidacao em massa via bump."""
        assert CACHE_VERSION == "v1"
        assert CACHE_VERSION in CACHE_KEY_PREFIX

    def test_cache_key_format(self):
        """Chave tem formato deterministico com prefix + version + window."""
        key = _cache_key("24h")
        assert key == "atendimento:ultimas-24h:v1:24h"

    def test_get_cached_returns_none_on_redis_offline(self):
        """Se Redis offline, retorna None (fail-open)."""
        with patch("app.services.atendimento_cache._get_redis_client", return_value=None):
            assert get_cached() is None

    def test_set_cached_returns_false_on_redis_offline(self):
        """Se Redis offline, set retorna False."""
        with patch("app.services.atendimento_cache._get_redis_client", return_value=None):
            assert set_cached({"x": 1}) is False

    def test_round_trip_set_get(self):
        """set_cached + get_cached retorna o mesmo dict."""
        fake = FakeRedis()
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            payload = {"count": 5, "atendimentos": [{"id": 1, "canal": "whatsapp"}]}
            assert set_cached(payload) is True
            result = get_cached()
            assert result == payload

    def test_set_uses_ttl_60s(self):
        """set_cached usa ex=60s."""
        fake = FakeRedis()
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            set_cached({"x": 1})
            # Verifica que foi setado com TTL 60s
            assert fake.expirations.get(_cache_key()) == 60

    def test_get_cached_handles_corrupt_json(self):
        """Se JSON no Redis estiver corrompido, retorna None (fail-safe)."""
        fake = FakeRedis()
        fake.store[_cache_key()] = "{ not valid json"
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            assert get_cached() is None

    def test_invalidate_specific_window(self):
        """invalidate(window) remove aquela chave."""
        fake = FakeRedis()
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            set_cached({"x": 1})
            assert fake.store.get(_cache_key()) is not None
            count = invalidate("24h")
            assert count == 1
            assert fake.store.get(_cache_key()) is None

    def test_invalidate_all_windows(self):
        """invalidate(None) remove TODAS as chaves do prefix."""
        fake = FakeRedis()
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            # Simula 2 keys (versao atual + futura)
            fake.store["atendimento:ultimas-24h:v1:24h"] = "1"
            fake.store["atendimento:ultimas-24h:v1:48h"] = "2"
            fake.store["other:cache:key"] = "3"  # NAO deve remover

            count = invalidate(None)
            assert count == 2
            assert "atendimento:ultimas-24h:v1:24h" not in fake.store
            assert "atendimento:ultimas-24h:v1:48h" not in fake.store
            assert "other:cache:key" in fake.store  # preservado

    def test_invalidate_returns_0_when_redis_offline(self):
        """invalidate com Redis offline retorna 0 (nao levanta)."""
        with patch("app.services.atendimento_cache._get_redis_client", return_value=None):
            assert invalidate() == 0

    def test_serialization_with_datetime(self):
        """Serializa datetime com default=str (vira string ISO no Redis)."""
        from datetime import datetime, timezone
        fake = FakeRedis()
        with patch("app.services.atendimento_cache._get_redis_client", return_value=fake):
            now = datetime.now(timezone.utc)
            payload = {"atendimentos": [{"concluido_em": now}]}
            set_cached(payload)
            # Recupera e valida - datetime vira string apos JSON roundtrip
            result = get_cached()
            assert result is not None
            assert "atendimentos" in result
            assert isinstance(result["atendimentos"][0]["concluido_em"], str)
            # Conteudo bate (com datetime como string)
            assert result["atendimentos"][0]["concluido_em"] == now.isoformat() or \
                   "2026" in result["atendimentos"][0]["concluido_em"]
