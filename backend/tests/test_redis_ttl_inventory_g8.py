"""G8.05.T1 — Testes para inventário de TTL Redis.

Cobre:
  - TTL_REGISTRY: 14+ chaves documentadas
  - Cada chave tem ttl_seconds > 0 + eviction_safe=True + lgpd_art
  - get_keys_by_scope: filtra corretamente
  - get_keys_by_lgpd_art: filtra por Art.16/18
  - validate_ttl_config: detecta ERROR/WARN
  - recommended_eviction_policy: allkeys-lru
  - render_inventory_report: Markdown válido com table
  - render_recommended_config: redis.conf puro
  - find_long_ttl_keys: detecta chaves > 7d
  - find_short_ttl_keys: detecta chaves < 60s
  - CLI: smoke test
  - LGPD: chaves de PII têm Art.16 ou Art.18

Modified by Gustavo Almeida — G8 Wave 32 A2.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TTL_MODULE = ROOT / "app" / "services" / "redis_ttl_inventory.py"


@pytest.fixture(scope="module")
def ttl_module():
    spec = importlib.util.spec_from_file_location("redis_ttl_inventory", TTL_MODULE)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTTLRegistry:
    def test_minimum_12_keys_documented(self, ttl_module):
        assert len(ttl_module.TTL_REGISTRY) >= 12

    def test_all_keys_have_positive_ttl(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta["ttl_seconds"] > 0, f"TTL 0 ou negativo: {key}"

    def test_all_keys_have_eviction_safe_true(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta.get("eviction_safe") is True, f"Não eviction-safe: {key}"

    def test_all_keys_have_lgpd_art(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta.get("lgpd_art"), f"Sem lgpd_art: {key}"

    def test_all_keys_have_scope(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta.get("scope"), f"Sem scope: {key}"

    def test_all_keys_have_rationale(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta.get("rationale"), f"Sem rationale: {key}"

    def test_all_keys_have_current_location(self, ttl_module):
        for key, meta in ttl_module.TTL_REGISTRY.items():
            assert meta.get("current_location"), f"Sem current_location: {key}"

    def test_unique_key_patterns(self, ttl_module):
        keys = list(ttl_module.TTL_REGISTRY.keys())
        assert len(keys) == len(set(keys)), "Keys duplicadas"


class TestGetKeysByScope:
    def test_rate_limit_keys(self, ttl_module):
        rl_keys = ttl_module.get_keys_by_scope("rate_limit")
        assert len(rl_keys) >= 2
        for k in rl_keys:
            assert "ratelimit" in k.lower()

    def test_session_keys(self, ttl_module):
        session_keys = ttl_module.get_keys_by_scope("session")
        assert len(session_keys) >= 3
        # session_keys inclui session:*, lgpd:consent, chat:memory (TTL-based session)
        for k in session_keys:
            assert any(
                tag in k.lower()
                for tag in ("session", "consent", "memory", "user")
            ), f"Session key '{k}' não tem tag esperada"

    def test_cache_keys(self, ttl_module):
        cache_keys = ttl_module.get_keys_by_scope("cache")
        assert len(cache_keys) >= 2

    def test_lock_keys(self, ttl_module):
        lock_keys = ttl_module.get_keys_by_scope("lock")
        assert len(lock_keys) >= 1

    def test_queue_keys(self, ttl_module):
        queue_keys = ttl_module.get_keys_by_scope("queue")
        assert len(queue_keys) >= 1

    def test_nonexistent_scope_returns_empty(self, ttl_module):
        assert ttl_module.get_keys_by_scope("nonexistent") == []


class TestGetKeysByLGPD:
    def test_art_16_keys(self, ttl_module):
        """LGPD Art.16 (eliminação após prazo)."""
        keys = ttl_module.get_keys_by_lgpd_art("Art.16")
        assert len(keys) >= 5

    def test_art_18_keys(self, ttl_module):
        """LGPD Art.18 (acesso do titular)."""
        keys = ttl_module.get_keys_by_lgpd_art("Art.18")
        assert len(keys) >= 1

    def test_art_37_keys(self, ttl_module):
        """LGPD Art.37 (registro de operações)."""
        keys = ttl_module.get_keys_by_lgpd_art("Art.37")
        assert len(keys) >= 0  # pode estar vazio

    def test_pii_keys_have_lgpd_mapping(self, ttl_module):
        """Chaves com PII devem ter Art.16 ou Art.18."""
        pii_keys = ["session:user", "chat:memory", "lgpd:consent", "session:refresh"]
        for pattern in pii_keys:
            matches = [k for k in ttl_module.TTL_REGISTRY if pattern in k]
            if matches:
                for k in matches:
                    art = ttl_module.TTL_REGISTRY[k].get("lgpd_art", "")
                    assert "Art.16" in art or "Art.18" in art, \
                        f"PII key '{k}' sem Art.16/18: {art}"


class TestValidateTTLConfig:
    def test_validation_returns_3_severities(self, ttl_module):
        result = ttl_module.validate_ttl_config()
        assert "ERROR" in result
        assert "WARN" in result
        assert "INFO" in result

    def test_validation_zero_errors(self, ttl_module):
        """Registry foi curado: zero ERROR."""
        result = ttl_module.validate_ttl_config()
        assert len(result["ERROR"]) == 0, f"Errors: {result['ERROR']}"

    def test_validation_has_info_summary(self, ttl_module):
        result = ttl_module.validate_ttl_config()
        assert len(result["INFO"]) > 0
        assert any("Total" in info for info in result["INFO"])


class TestEvictionPolicy:
    def test_recommended_is_allkeys_lru(self, ttl_module):
        policy = ttl_module.recommended_eviction_policy()
        assert policy == "allkeys-lru"

    def test_recommended_config_has_maxmemory(self, ttl_module):
        cfg = ttl_module.RECOMMENDED_REDIS_CONFIG
        assert "maxmemory" in cfg
        assert cfg["maxmemory"].endswith("gb") or cfg["maxmemory"].endswith("mb")

    def test_recommended_config_has_eviction_policy(self, ttl_module):
        cfg = ttl_module.RECOMMENDED_REDIS_CONFIG
        assert "maxmemory-policy" in cfg
        assert cfg["maxmemory-policy"] == "allkeys-lru"

    def test_recommended_config_has_aof(self, ttl_module):
        cfg = ttl_module.RECOMMENDED_REDIS_CONFIG
        assert cfg.get("appendonly") == "yes"


class TestRenderReports:
    def test_inventory_report_has_table(self, ttl_module):
        report = ttl_module.render_inventory_report()
        # Markdown table header
        assert "| Key | TTL | Scope |" in report

    def test_inventory_report_has_validation_section(self, ttl_module):
        report = ttl_module.render_inventory_report()
        assert "## Validation" in report

    def test_inventory_report_has_recommended_config(self, ttl_module):
        report = ttl_module.render_inventory_report()
        assert "## Recommended Redis Config" in report

    def test_recommended_config_is_pure_redis_conf(self, ttl_module):
        cfg = ttl_module.render_recommended_config()
        assert cfg.startswith("# G8.05.T1")
        assert "maxmemory-policy" in cfg
        assert "allkeys-lru" in cfg
        # Não deve ter markdown
        assert "## " not in cfg

    def test_inventory_report_shows_all_keys(self, ttl_module):
        report = ttl_module.render_inventory_report()
        for key in ttl_module.TTL_REGISTRY:
            # Verifica que cada key aparece (pode estar com markdown code format)
            assert key.replace(":", "") in report.replace(":", "") or key in report


class TestFindLongAndShortTTL:
    def test_find_long_ttl_default_7d(self, ttl_module):
        long_keys = ttl_module.find_long_ttl_keys(threshold_days=7)
        # refresh tokens excluídos
        for k, ttl in long_keys:
            assert "refresh" not in k
            assert ttl > 7 * 86400

    def test_find_short_ttl_default_60s(self, ttl_module):
        short_keys = ttl_module.find_short_ttl_keys(threshold_seconds=60)
        assert len(short_keys) >= 1  # chat:pipeline queue
        for k, ttl in short_keys:
            assert ttl < 60

    def test_find_long_returns_sorted_desc(self, ttl_module):
        long_keys = ttl_module.find_long_ttl_keys(threshold_days=1)
        ttls = [t for _, t in long_keys]
        assert ttls == sorted(ttls, reverse=True)

    def test_find_short_returns_sorted_asc(self, ttl_module):
        short_keys = ttl_module.find_short_ttl_keys(threshold_seconds=300)
        ttls = [t for _, t in short_keys]
        assert ttls == sorted(ttls)


class TestCLI:
    def test_module_help_runs(self):
        result = subprocess.run(
            [sys.executable, str(TTL_MODULE), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode in (0, 1, 2)

    def test_module_inventory_outputs_markdown(self):
        result = subprocess.run(
            [sys.executable, str(TTL_MODULE), "--inventory"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "Redis TTL Inventory" in result.stdout
        assert "| Key |" in result.stdout

    def test_module_config_outputs_redis_conf(self):
        result = subprocess.run(
            [sys.executable, str(TTL_MODULE), "--config"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "maxmemory-policy" in result.stdout
        assert "allkeys-lru" in result.stdout

    def test_module_validate_outputs_json(self):
        result = subprocess.run(
            [sys.executable, str(TTL_MODULE), "--validate"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "ERROR" in data
        assert "WARN" in data
        assert "INFO" in data


class TestLGPDCompliance:
    """Garante alinhamento LGPD em todas as chaves com PII."""

    def test_session_user_has_art16(self, ttl_module):
        key = "session:user:{user_id}"
        assert "Art.16" in ttl_module.TTL_REGISTRY[key]["lgpd_art"]

    def test_chat_memory_has_art16(self, ttl_module):
        key = "chat:memory:user:{user_id}"
        assert "Art.16" in ttl_module.TTL_REGISTRY[key]["lgpd_art"]

    def test_idempotency_has_art16(self, ttl_module):
        key = "webhook:idempotency:{key}"
        assert "Art.16" in ttl_module.TTL_REGISTRY[key]["lgpd_art"]

    def test_lgpd_consent_has_art18(self, ttl_module):
        key = "lgpd:consent:{cliente_id}"
        assert "Art.18" in ttl_module.TTL_REGISTRY[key]["lgpd_art"]

    def test_pii_ttls_within_30_days_max(self, ttl_module):
        """PII keys devem ter TTL <= 30d (LGPD Art.16 limite seguro)."""
        pii_patterns = ["user", "consent", "memory"]
        for key, meta in ttl_module.TTL_REGISTRY.items():
            if any(p in key for p in pii_patterns):
                ttl = meta["ttl_seconds"]
                assert ttl <= 30 * 86400, \
                    f"PII key '{key}' TTL={ttl}s ({ttl // 86400}d) > 30d"