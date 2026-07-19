"""G8.09.T3 — PII/logs traffic policy: private tunnels only.

Assegura que export de logs e sinks com dados pessoais (PII) só apontem
para hosts privados / Tailscale / MagicDNS — nunca IP ou DNS público.

Reutiliza `is_private_host` e `extract_hosts_from_url` de magicdns_inventory
(G8.09.T2).

API:
- is_log_export_allowed(destination_host) -> bool
- classify_log_sink(url) -> 'allowed' | 'blocked' | 'unknown'
- assert_pii_sink_safe(url) -> None  (raises ValueError se público)
- policy_summary() -> list[str]  (regras humanas)

Modified by Gustavo Almeida — Wave 40 / G8 Squad 09.
"""

from __future__ import annotations

from typing import Literal

from app.services.magicdns_inventory import extract_hosts_from_url, is_private_host

SinkClass = Literal["allowed", "blocked", "unknown"]

# Regras documentadas (policy_summary) — fonte única para docs/ops
_POLICY_RULES: tuple[str, ...] = (
    "Log export e sinks com PII só podem usar hosts privados (RFC1918, Tailscale CGNAT 100.x, loopback).",
    "Nomes MagicDNS/Tailscale (*.ts.net), .local e service names de swarm (sem ponto) são permitidos.",
    "Hosts canônicos internos (cartorio_postgres, cartorio_redis, cartorio-api, etc.) são permitidos.",
    "IPs públicos e DNS públicos (ex.: 8.8.8.8, logs.example.com) são bloqueados para PII/logs.",
    "URL vazia ou sem host extraível classifica como unknown (não é considerada segura).",
    "assert_pii_sink_safe(url) levanta ValueError se o sink não for allowed.",
)


def is_log_export_allowed(destination_host: str) -> bool:
    """Retorna True se o host de destino de log/export é privado ou Tailscale.

    Args:
        destination_host: hostname ou IP (sem scheme/path).

    Returns:
        True apenas para hosts classificados como privados por is_private_host.
    """
    return is_private_host(destination_host)


def classify_log_sink(url: str) -> SinkClass:
    """Classifica um sink de log/PII a partir de URL ou host.

    Returns:
        'allowed'  — host privado/Tailscale/MagicDNS
        'blocked'  — host público identificável
        'unknown'  — URL vazia ou host não extraível
    """
    raw = (url or "").strip()
    if not raw:
        return "unknown"

    hosts = extract_hosts_from_url(raw)
    # bare hostname (sem scheme) — extract_hosts_from_url ainda devolve o host
    if not hosts:
        # tenta como host nu
        if is_private_host(raw):
            return "allowed"
        # se parece host com ponto e não é privado → blocked; senão unknown
        if "." in raw and " " not in raw:
            return "blocked"
        return "unknown"

    host = hosts[0]
    if not host:
        return "unknown"
    if is_private_host(host):
        return "allowed"
    return "blocked"


def assert_pii_sink_safe(url: str) -> None:
    """Garante que o sink de PII/logs é privado; levanta ValueError se não.

    Args:
        url: URL ou host do sink (Sentry DSN parcial, OTLP endpoint, syslog, etc.).

    Raises:
        ValueError: se classificado como blocked ou unknown (PII não pode ir a sink incerto).
    """
    classification = classify_log_sink(url)
    if classification == "allowed":
        return
    raise ValueError(
        f"PII/log sink not allowed on private tunnels only policy: "
        f"url={url!r} classification={classification!r}. "
        f"Use Tailscale/MagicDNS/RFC1918 hosts only."
    )


def policy_summary() -> list[str]:
    """Lista legível das regras da política de túneis privados para PII/logs."""
    return list(_POLICY_RULES)


__all__ = [
    "SinkClass",
    "assert_pii_sink_safe",
    "classify_log_sink",
    "is_log_export_allowed",
    "policy_summary",
]
