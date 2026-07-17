"""G8.09.T4 — SSH access validation via authorized Tailscale peers.

Inventário de nós autorizados a iniciar SSH na VPS mesh e validação soft
de blocos `sshd_config` (AllowUsers / Match Address 100.*).

API:
  - AuthorizedPeer(name, ip, role)
  - DEFAULT_PEERS — inventário canônico (PROMPT.json tailscale.nodes)
  - is_ssh_source_allowed(source_ip, peers=None) -> bool
  - validate_sshd_match_block(config_text) — soft parse AllowUsers/Match Address 100.
  - list_authorized_ips() / peer_by_ip() / inventory_report()

Regras:
  - Fonte SSH permitida apenas se IP ∈ peers (default: mesh Tailscale).
  - IP da própria VPS (100.99.172.84) está no inventário com role admin.
  - validate_sshd_match_block é soft: não executa sshd; só inspeciona texto.

Modified by Gustavo Almeida — G8.09.T4 Wave 37 Squad 09.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

# Tailscale CGNAT (RFC 6598) — prefixo esperado em Match Address
TAILSCALE_CGNAT_PREFIX: str = '100.'
VPS_TAILSCALE_IP: str = '100.99.172.84'
VPS_PEER_NAME: str = 'vps-cartorio'


@dataclass(frozen=True, slots=True)
class AuthorizedPeer:
    """Nó Tailscale autorizado a acessar SSH (ou destino admin canônico)."""

    name: str
    ip: str
    role: str  # admin | ops | device | breakglass


# Inventário canônico (PROMPT.json infrastructure.tailscale.nodes).
# VPS 100.99.172.84 = admin (destino SSH / nó mesh principal).
DEFAULT_PEERS: tuple[AuthorizedPeer, ...] = (
    AuthorizedPeer(name='vps-cartorio', ip='100.99.172.84', role='admin'),
    AuthorizedPeer(name='macbook-pro-gus', ip='100.83.180.16', role='admin'),
    AuthorizedPeer(name='iphone-17-pro', ip='100.122.101.33', role='device'),
    AuthorizedPeer(name='iphone-andre', ip='100.74.36.41', role='device'),
    AuthorizedPeer(name='triqhub', ip='100.110.127.44', role='ops'),
)


@dataclass(slots=True)
class SshdMatchValidation:
    """Resultado soft-parse de trecho/arquivo sshd_config."""

    ok: bool
    has_match_address_100: bool
    has_allow_users: bool
    allow_users: list[str] = field(default_factory=list)
    match_addresses: list[str] = field(default_factory=list)
    detail: str = ''

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_IP_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}$')
# Match Address 100.64.0.0/10 | Match Address 100.* | Match Address 100.99.172.84
_MATCH_ADDR_RE = re.compile(
    r'(?im)^\s*Match\s+Address\s+(\S+)',
)
_ALLOW_USERS_RE = re.compile(
    r'(?im)^\s*AllowUsers\s+(.+?)\s*$',
)


def _normalize_ip(source_ip: str) -> str:
    """Normaliza IP de origem (strip, drop zone/port se vier host:port)."""
    s = (source_ip or '').strip()
    if not s:
        return ''
    # [ipv6] not expected for Tailscale CGNAT IPv4 inventory
    if s.startswith('[') and ']' in s:
        s = s[1 : s.index(']')]
    if s.count(':') == 1 and _IP_RE.match(s.split(':', 1)[0]):
        s = s.split(':', 1)[0]
    return s.strip()


def list_authorized_ips(
    peers: Sequence[AuthorizedPeer] | None = None,
) -> frozenset[str]:
    """Conjunto de IPs autorizados."""
    src = peers if peers is not None else DEFAULT_PEERS
    return frozenset(p.ip for p in src)


def peer_by_ip(
    ip: str,
    peers: Sequence[AuthorizedPeer] | None = None,
) -> AuthorizedPeer | None:
    """Retorna o peer com o IP dado, ou None."""
    needle = _normalize_ip(ip)
    src = peers if peers is not None else DEFAULT_PEERS
    for p in src:
        if p.ip == needle:
            return p
    return None


def is_ssh_source_allowed(
    source_ip: str,
    peers: Sequence[AuthorizedPeer] | None = None,
) -> bool:
    """True se source_ip está no inventário de peers autorizados.

    Args:
        source_ip: IP do cliente que inicia a sessão SSH.
        peers: lista opcional (default: DEFAULT_PEERS).

    Returns:
        bool — permitido apenas se IP exact-match no inventário.
    """
    ip = _normalize_ip(source_ip)
    if not ip or not _IP_RE.match(ip):
        return False
    return ip in list_authorized_ips(peers)


def validate_sshd_match_block(config_text: str) -> SshdMatchValidation:
    """Soft-parse de sshd_config: procura AllowUsers e Match Address 100.*.

    Não invoca `sshd -T`. Útil para CI/docs e drift detection em drop-ins.

    Critério ok:
      - existe pelo menos um `Match Address` cujo valor começa com `100.`
        (CGNAT Tailscale) OU contém `100.64` / `100.`;
      - e existe `AllowUsers` (qualquer lista não vazia).

    Soft: se o texto estiver vazio, ok=False com detail explícito.
    """
    text = config_text or ''
    if not text.strip():
        return SshdMatchValidation(
            ok=False,
            has_match_address_100=False,
            has_allow_users=False,
            detail='empty config_text',
        )

    match_addrs = [m.group(1).strip() for m in _MATCH_ADDR_RE.finditer(text)]
    has_match_100 = any(
        a.startswith(TAILSCALE_CGNAT_PREFIX)
        or a.startswith('100.64')
        or '/10' in a
        and '100.' in a
        for a in match_addrs
    )
    # reforço: linha Match Address 100. em qualquer forma
    if not has_match_100:
        has_match_100 = bool(
            re.search(r'(?im)^\s*Match\s+Address\s+100\.', text)
        )

    allow_users: list[str] = []
    for m in _ALLOW_USERS_RE.finditer(text):
        parts = m.group(1).strip().split()
        allow_users.extend(parts)
    has_allow = len(allow_users) > 0

    ok = has_match_100 and has_allow
    detail_parts: list[str] = []
    if not has_match_100:
        detail_parts.append('missing Match Address 100.*')
    if not has_allow:
        detail_parts.append('missing AllowUsers')
    if ok:
        detail_parts.append(
            f'ok match={match_addrs!r} allow_users={allow_users!r}'
        )

    return SshdMatchValidation(
        ok=ok,
        has_match_address_100=has_match_100,
        has_allow_users=has_allow,
        allow_users=allow_users,
        match_addresses=match_addrs,
        detail='; '.join(detail_parts),
    )


def inventory_report(
    peers: Iterable[AuthorizedPeer] | None = None,
) -> dict[str, Any]:
    """Relatório JSON-serializável do inventário."""
    src = list(peers) if peers is not None else list(DEFAULT_PEERS)
    return {
        'vps_tailscale_ip': VPS_TAILSCALE_IP,
        'count': len(src),
        'peers': [asdict(p) for p in src],
        'authorized_ips': sorted(p.ip for p in src),
    }


def recommended_sshd_snippet() -> str:
    """Snippet sugerido (docs / ops) — não aplicado automaticamente."""
    allow = ' '.join(
        sorted({p.role for p in DEFAULT_PEERS if p.role == 'admin'})
    )
    # AllowUsers tipicamente usa logins Linux, não roles mesh —
    # documentamos root + Match Address Tailscale CGNAT.
    return (
        '# G8.09.T4 — SSH only from Tailscale CGNAT (soft template)\n'
        'AllowUsers root\n'
        'Match Address 100.64.0.0/10\n'
        '    PermitRootLogin prohibit-password\n'
        '    PasswordAuthentication no\n'
        f'# VPS mesh target: {VPS_PEER_NAME} {VPS_TAILSCALE_IP} admin\n'
        f'# roles note: {allow or "admin"}\n'
    )


__all__ = [
    'AuthorizedPeer',
    'DEFAULT_PEERS',
    'SshdMatchValidation',
    'TAILSCALE_CGNAT_PREFIX',
    'VPS_PEER_NAME',
    'VPS_TAILSCALE_IP',
    'inventory_report',
    'is_ssh_source_allowed',
    'list_authorized_ips',
    'peer_by_ip',
    'recommended_sshd_snippet',
    'validate_sshd_match_block',
]
