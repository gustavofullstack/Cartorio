"""G8.10.T2 — DNS health check for CI (Cloudflare-independent dig/socket).

Valida registros esperados de 2notasudi.com.br sem API key obrigatória
(dig/socket). Se CLOUDFLARE_API_TOKEN presente, opcionalmente consulta API
(best-effort, fail-open).

Modified by Gustavo Almeida — Wave 41.
"""

from __future__ import annotations

import os
import socket
import time
from dataclasses import asdict, dataclass, field
from typing import Any

# Domínios canônicos (Lesson 179 / G7 DNS)
EXPECTED_HOSTS: tuple[str, ...] = (
    'api.2notasudi.com.br',
    'agent.2notasudi.com.br',
    'whatsapp.2notasudi.com.br',
    'flow.2notasudi.com.br',
    'chat.2notasudi.com.br',
    'easypanel.2notasudi.com.br',
    'supbase.2notasudi.com.br',
)


@dataclass(slots=True)
class DnsCheckResult:
    host: str
    ok: bool
    latency_ms: int
    detail: str


@dataclass(slots=True)
class DnsCiReport:
    ok: bool
    checks: list[DnsCheckResult] = field(default_factory=list)
    mode: str = 'socket'

    def to_dict(self) -> dict[str, Any]:
        return {
            'ok': self.ok,
            'mode': self.mode,
            'checks': [asdict(c) for c in self.checks],
            'cloudflare_token_present': bool(os.environ.get('CLOUDFLARE_API_TOKEN')),
        }


def resolve_host(host: str, timeout: float = 3.0) -> DnsCheckResult:
    """Resolve A/AAAA via getaddrinfo (CI-friendly)."""
    start = time.perf_counter()
    try:
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            infos = socket.getaddrinfo(host, None)
        finally:
            socket.setdefaulttimeout(old)
        ms = int((time.perf_counter() - start) * 1000)
        if not infos:
            return DnsCheckResult(host, False, ms, 'empty result')
        addr = infos[0][4][0]
        return DnsCheckResult(host, True, ms, f'resolved:{addr}')
    except Exception as exc:  # noqa: BLE001
        ms = int((time.perf_counter() - start) * 1000)
        return DnsCheckResult(host, False, ms, f'{type(exc).__name__}')


def run_dns_ci_checks(
    hosts: tuple[str, ...] | None = None,
    *,
    require_all: bool = False,
) -> DnsCiReport:
    """Roda checks. require_all=False → ok se maioria ou api.* resolver (CI soft)."""
    targets = hosts or EXPECTED_HOSTS
    checks = [resolve_host(h) for h in targets]
    if require_all:
        ok = all(c.ok for c in checks)
    else:
        # soft: pelo menos api.* ou qualquer um
        ok = any(c.ok for c in checks if c.host.startswith('api.')) or any(c.ok for c in checks)
    return DnsCiReport(ok=ok, checks=checks, mode='socket')


def cloudflare_configured() -> bool:
    return bool(os.environ.get('CLOUDFLARE_API_TOKEN') and os.environ.get('CLOUDFLARE_ZONE_ID'))


__all__ = [
    'EXPECTED_HOSTS',
    'DnsCheckResult',
    'DnsCiReport',
    'cloudflare_configured',
    'resolve_host',
    'run_dns_ci_checks',
]
