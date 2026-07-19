"""G8.09.T2 — MagicDNS / private DNS inventory for internal DB+API.

Documenta e valida que serviços sensíveis usam nomes Tailscale/MagicDNS
ou hosts privados — não IPs públicos expostos em config de app.

Modified by Gustavo Almeida — Wave 40.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# Hosts internos canônicos (Tailscale / MagicDNS / swarm)
DEFAULT_PRIVATE_HOSTS: tuple[str, ...] = (
    "cartorio-api",
    "cartorio_api",
    "cartorio_postgres",
    "cartorio_redis",
    "cartorio_chatwoot",
    "cartorio-postgres",
    "100.99.172.84",  # Tailscale VPS (G8.09.T1)
    "postgres",
    "redis",
)

_PUBLIC_IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
# RFC1918 + Tailscale CGNAT 100.64/10
_PRIVATE_PREFIXES = (
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.2",
    "172.3",
    "100.",  # Tailscale CGNAT
    "127.",
)


@dataclass(slots=True)
class MagicDnsCheck:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True)
class MagicDnsReport:
    ok: bool
    checks: list[MagicDnsCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checks": [asdict(c) for c in self.checks]}


def is_private_host(host: str) -> bool:
    h = (host or "").strip().lower()
    if not h:
        return False
    if h in {x.lower() for x in DEFAULT_PRIVATE_HOSTS}:
        return True
    if h.endswith(".ts.net") or h.endswith(".local"):
        return True
    if _PUBLIC_IP_RE.fullmatch(h) or _PUBLIC_IP_RE.match(h):
        return any(h.startswith(p) for p in _PRIVATE_PREFIXES)
    # bare service names (no dots) treated as private (swarm DNS)
    if "." not in h:
        return True
    return False


def extract_hosts_from_url(url: str) -> list[str]:
    """Extrai host de URLs postgres/redis/http simples."""
    if not url:
        return []
    # strip scheme
    u = url
    if "://" in u:
        u = u.split("://", 1)[1]
    # strip path/user
    if "@" in u:
        u = u.rsplit("@", 1)[-1]
    hostport = u.split("/")[0]
    host = hostport.split(":")[0]
    return [host] if host else []


def validate_connection_urls(urls: dict[str, str]) -> MagicDnsReport:
    """Valida mapa nome→URL; falha se host público literal."""
    checks: list[MagicDnsCheck] = []
    for name, url in urls.items():
        hosts = extract_hosts_from_url(url)
        if not hosts:
            checks.append(MagicDnsCheck(name, False, "empty url"))
            continue
        host = hosts[0]
        priv = is_private_host(host)
        checks.append(
            MagicDnsCheck(
                name,
                priv,
                f"host={host} private={priv}",
            )
        )
    ok = all(c.ok for c in checks) if checks else False
    return MagicDnsReport(ok=ok, checks=checks)


def recommended_magicdns_map() -> dict[str, str]:
    """Mapa recomendado para docs / MagicDNS."""
    return {
        "api": "cartorio-api:8000",
        "postgres": "cartorio_postgres:5432",
        "redis": "cartorio_redis:6379",
        "vps_tailscale_ssh": "100.99.172.84:22",
    }


__all__ = [
    "DEFAULT_PRIVATE_HOSTS",
    "MagicDnsCheck",
    "MagicDnsReport",
    "extract_hosts_from_url",
    "is_private_host",
    "recommended_magicdns_map",
    "validate_connection_urls",
]
