"""G8.09.T3 — Private tunnel policy for PII/logs (unit tests).

Modified by Gustavo Almeida — Wave 40.
"""

from __future__ import annotations

import pytest

from app.services.private_tunnel_policy import (
    assert_pii_sink_safe,
    classify_log_sink,
    is_log_export_allowed,
    policy_summary,
)


def test_log_export_allowed_private_swarm() -> None:
    assert is_log_export_allowed('cartorio_postgres') is True
    assert is_log_export_allowed('redis') is True
    assert is_log_export_allowed('cartorio-api') is True


def test_log_export_allowed_tailscale() -> None:
    assert is_log_export_allowed('100.99.172.84') is True
    assert is_log_export_allowed('vps.tail123.ts.net') is True
    assert is_log_export_allowed('logs.local') is True


def test_log_export_blocked_public() -> None:
    assert is_log_export_allowed('187.77.236.77') is False
    assert is_log_export_allowed('8.8.8.8') is False
    assert is_log_export_allowed('logs.example.com') is False


def test_log_export_empty_host() -> None:
    assert is_log_export_allowed('') is False
    assert is_log_export_allowed('   ') is False


def test_classify_log_sink_allowed_urls() -> None:
    assert classify_log_sink('https://cartorio_redis:6379/0') == 'allowed'
    assert classify_log_sink('otlp://100.99.172.84:4317') == 'allowed'
    assert classify_log_sink('http://vps.tail123.ts.net:3100/loki') == 'allowed'
    assert classify_log_sink('syslog://postgres:514') == 'allowed'


def test_classify_log_sink_blocked_urls() -> None:
    assert classify_log_sink('https://logs.example.com/v1/ingest') == 'blocked'
    assert classify_log_sink('https://8.8.8.8:443/logs') == 'blocked'
    assert classify_log_sink('http://187.77.236.77:3100') == 'blocked'


def test_classify_log_sink_unknown() -> None:
    assert classify_log_sink('') == 'unknown'
    assert classify_log_sink('   ') == 'unknown'


def test_assert_pii_sink_safe_ok() -> None:
    assert_pii_sink_safe('https://cartorio-api:8000/internal/logs')
    assert_pii_sink_safe('otlp://100.99.172.84:4317')
    assert_pii_sink_safe('redis://cartorio_redis:6379/0')


def test_assert_pii_sink_safe_public_raises() -> None:
    with pytest.raises(ValueError, match='not allowed|private tunnels'):
        assert_pii_sink_safe('https://sentry.io/api/123/store/')
    with pytest.raises(ValueError):
        assert_pii_sink_safe('https://8.8.8.8/logs')


def test_assert_pii_sink_safe_unknown_raises() -> None:
    with pytest.raises(ValueError):
        assert_pii_sink_safe('')


def test_policy_summary_nonempty() -> None:
    rules = policy_summary()
    assert isinstance(rules, list)
    assert len(rules) >= 4
    assert all(isinstance(r, str) and r.strip() for r in rules)
    # deve mencionar túneis/privados/PII de forma legível
    joined = ' '.join(rules).lower()
    assert 'privado' in joined or 'private' in joined or 'tailscale' in joined
