"""G8.09.T2 — MagicDNS inventory tests.

Modified by Gustavo Almeida — Wave 40.
"""

from __future__ import annotations

from app.services.magicdns_inventory import (
    extract_hosts_from_url,
    is_private_host,
    recommended_magicdns_map,
    validate_connection_urls,
)


def test_private_swarm_names() -> None:
    assert is_private_host("cartorio_postgres") is True
    assert is_private_host("redis") is True


def test_tailscale_ip() -> None:
    assert is_private_host("100.99.172.84") is True


def test_public_ip_rejected() -> None:
    assert is_private_host("187.77.236.77") is False


def test_ts_net() -> None:
    assert is_private_host("vps.tail123.ts.net") is True


def test_extract_host() -> None:
    assert extract_hosts_from_url("postgresql://user:pass@cartorio_postgres:5432/db") == [
        "cartorio_postgres"
    ]


def test_validate_urls_ok() -> None:
    r = validate_connection_urls(
        {
            "db": "postgresql://u:p@cartorio_postgres:5432/x",
            "redis": "redis://cartorio_redis:6379/0",
        }
    )
    assert r.ok is True


def test_validate_urls_public_fails() -> None:
    r = validate_connection_urls({"db": "postgresql://u:p@8.8.8.8:5432/x"})
    assert r.ok is False


def test_recommended_map() -> None:
    m = recommended_magicdns_map()
    assert "postgres" in m
    assert "api" in m
