"""Health Radar Expanded (F6 [P2] 2026-07-15).

Estende o radar existente (`/api/v1/health/radar`) com 5 categorias
adicionais de checks (DNS, Traefik routers, SSH VPS, Tailscale, Disk space).

Endpoint: GET /api/v1/health/radar/expanded

Categorias:
- health    : 7 servicos (database, redis, openclaw, chatwoot, supabase, n8n, evolution)
- dns       : 10 dominios do F4 SRE
- traefik   : routers HTTPS dos dominios (status_code 200/302/401/403 = UP; 404 + content-length 2901 = WARN router sem match)
- ssh       : porta SSH do VPS Hostinger (187.77.236.77:22) UP/DOWN
- tailscale : porta SSH Tailscale (100.99.172.84:22) UP/DOWN
- disk      : espaco livre em /var/lib/docker/volumes (free GB)
- mcp       : inventário de tools MCP (G8.07.T4)
- openclaw  : status dedicado do gateway OpenClaw (G8.04.T1)

Cada check retorna:
{
  "status": "up" | "down" | "warn",
  "latency_ms": int,
  "detail": str
}

Falha em qualquer check NAO quebra o endpoint (fail-open).
Todas as verificacoes sao executadas em paralelo via asyncio.gather.

Squad cartorio-front / F6 [P2] / 2026-07-15.
Modified by Gustavo Almeida.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import socket
import time
from typing import Any, cast

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db import engine

logger = logging.getLogger("cartorio.health_radar_expanded")

expanded_router = APIRouter()

# Dominios monitorados (F4 SRE + Lesson 179 Cloudflare + Wave 13 G6.D.T6).
# Inclui aliases NXDOMAIN (chatwoot/n8n/supabase) e canonicos em uso
# (chat/flow/whatsapp/supbase typo ACEITO — ver DOMAIN_TYPO_DECISION.md).
RADAR_DNS_DOMAINS: tuple[str, ...] = (
    "2notasudi.com.br",
    "api.2notasudi.com.br",
    "agent.2notasudi.com.br",
    "whatsapp.2notasudi.com.br",
    "chat.2notasudi.com.br",
    "flow.2notasudi.com.br",
    "easypanel.2notasudi.com.br",
    "supbase.2notasudi.com.br",  # typo ACEITO em prod (Lesson 179)
    "n8n.2notasudi.com.br",  # NXDOMAIN HOLD-GUSTAVO (alias desejado)
    "chatwoot.2notasudi.com.br",  # NXDOMAIN HOLD-GUSTAVO
    "supabase.2notasudi.com.br",  # NXDOMAIN HOLD-GUSTAVO
    "evo.2notasudi.com.br",
)

# Endpoints HTTPS para check Traefik router (HEAD para performance).
RADAR_TRAEFIK_DOMAINS: tuple[str, ...] = (
    "api.2notasudi.com.br",
    "agent.2notasudi.com.br",
    "whatsapp.2notasudi.com.br",
    "chat.2notasudi.com.br",
    "flow.2notasudi.com.br",
    "easypanel.2notasudi.com.br",
    "supbase.2notasudi.com.br",
)

# SSH / Tailscale endpoints (host:port).
RADAR_SSH_HOST: str = "187.77.236.77"
RADAR_SSH_PORT: int = 22
RADAR_TAILSCALE_HOST: str = "100.99.172.84"
RADAR_TAILSCALE_PORT: int = 22

# Disk path monitorado (volumes Docker).
RADAR_DISK_PATH: str = "/var/lib/docker/volumes"
TRAEFIK_WARN_CONTENT_LENGTH: int = 2901  # Traefik "router not found" response size
TRAEFIK_SOCKET_TIMEOUT: float = 3.0
SSH_SOCKET_TIMEOUT: float = 3.0


async def _check_dns(domain: str) -> dict[str, Any]:
    """Resolve DNS via `dig +short`. NXDOMAIN = down, NXDOMAIN via asyncio fail = warn.

    Args:
        domain: hostname a ser resolvido.

    Returns:
        Dict com status (up/down/warn), latency_ms, detail.
    """
    start = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_exec(
            "dig",
            "+short",
            domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        out = stdout.decode().strip()
        if out and proc.returncode == 0:
            return {
                "status": "up",
                "latency_ms": elapsed_ms,
                "detail": f"resolved: {out.splitlines()[0][:60]}",
            }
        return {
            "status": "down",
            "latency_ms": elapsed_ms,
            "detail": f"NXDOMAIN (rc={proc.returncode}, stderr={stderr.decode().strip()[:100]})",
        }
    except FileNotFoundError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "warn",
            "latency_ms": elapsed_ms,
            "detail": "dig binary not installed; cannot resolve",
        }
    except (TimeoutError, asyncio.TimeoutError):
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": "dig timeout (>3s)",
        }
    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
        }


async def _check_traefik(domain: str) -> dict[str, Any]:
    """HEAD https://<domain> — 200/302 = up; 404 com content-length 2901 = warn (router sem match).

    Args:
        domain: hostname cujo router Traefik deve estar configurado.

    Returns:
        Dict com status (up/down/warn), latency_ms, detail.
    """
    start = time.perf_counter()
    url = f"https://{domain}/"
    try:
        async with httpx.AsyncClient(timeout=TRAEFIK_SOCKET_TIMEOUT, verify=False) as client:
            resp = await client.head(url, follow_redirects=False)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        content_length = int(resp.headers.get("content-length", 0) or 0)
        if resp.status_code in (200, 301, 302):
            return {
                "status": "up",
                "latency_ms": elapsed_ms,
                "detail": f"HTTP {resp.status_code}",
            }
        if resp.status_code == 404 and content_length == TRAEFIK_WARN_CONTENT_LENGTH:
            return {
                "status": "warn",
                "latency_ms": elapsed_ms,
                "detail": (
                    f"Traefik router not matched (404 + content-length={content_length}). "
                    f"Possivel causa: dominio sem router configurado ou servico offline."
                ),
            }
        return {
            "status": "down",
            "latency_ms": elapsed_ms,
            "detail": f"HTTP {resp.status_code} (cl={content_length})",
        }
    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
        }


async def _check_socket(host: str, port: int, timeout: float = SSH_SOCKET_TIMEOUT) -> dict[str, Any]:
    """TCP socket connect check (host:port). UP = open; DOWN = connection refused/timeout.

    Args:
        host: hostname ou IP.
        port: porta TCP.
        timeout: timeout em segundos.

    Returns:
        Dict com status (up/down), latency_ms, detail.
    """
    start = time.perf_counter()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "up",
            "latency_ms": elapsed_ms,
            "detail": f"{host}:{port} open",
        }
    except (TimeoutError, asyncio.TimeoutError):
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{host}:{port} timeout (>{timeout}s)",
        }
    except (ConnectionRefusedError, OSError) as exc:
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{host}:{port} {type(exc).__name__}: {str(exc)[:120]}",
        }
    except Exception as exc:
        return {
            "status": "down",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{host}:{port} {type(exc).__name__}: {str(exc)[:120]}",
        }


def _check_disk(path: str) -> dict[str, Any]:
    """Disk space check via shutil.disk_usage. Falha = warn (nao down).

    Args:
        path: filesystem path para inspecionar.

    Returns:
        Dict com status (up/warn), latency_ms, detail.
    """
    start = time.perf_counter()
    try:
        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        percent_used = (usage.used / usage.total) * 100 if usage.total else 0
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        status = "warn" if percent_used > 85 else "up"
        return {
            "status": status,
            "latency_ms": elapsed_ms,
            "detail": f"free={free_gb:.2f}GB / total={total_gb:.2f}GB ({percent_used:.1f}% used)",
        }
    except FileNotFoundError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "warn",
            "latency_ms": elapsed_ms,
            "detail": f"path '{path}' not found on this host (non-Docker env?)",
        }
    except Exception as exc:
        return {
            "status": "warn",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
        }


async def _check_health_category() -> dict[str, dict[str, Any]]:
    """Health multi-servico (mesmo padrao do /health/radar existente).

    Returns:
        Dict servico -> status dict.
    """
    results: dict[str, dict[str, Any]] = {}

    db_ok = False
    db_start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        results["database_error"] = {
            "status": "down",
            "latency_ms": int((time.perf_counter() - db_start) * 1000),
            "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
        }
    results["database"] = {
        "status": "up" if db_ok else "down",
        "latency_ms": int((time.perf_counter() - db_start) * 1000),
        "detail": "SQLAlchemy engine.connect() SELECT 1" if db_ok else "engine.connect failed",
    }

    redis_ok = False
    redis_start = time.perf_counter()
    try:
        import redis  # noqa: PLC0415

        r = redis.from_url(settings.redis_url, socket_timeout=2.0)
        r.ping()
        redis_ok = True
    except Exception as exc:
        results["redis_error"] = {
            "status": "down",
            "latency_ms": int((time.perf_counter() - redis_start) * 1000),
            "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
        }
    results["redis"] = {
        "status": "up" if redis_ok else "down",
        "latency_ms": int((time.perf_counter() - redis_start) * 1000),
        "detail": "Redis PING" if redis_ok else "redis.from_url/ping failed",
    }

    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in [
            ("openclaw", f"{settings.openclaw_base_url}/health"),
            ("evolution", f"{settings.evolution_base_url}/"),
        ]:
            s = time.perf_counter()
            try:
                resp = await client.get(url)
                elapsed_ms = int((time.perf_counter() - s) * 1000)
                ok = resp.status_code == 200
                results[name] = {
                    "status": "up" if ok else "down",
                    "latency_ms": elapsed_ms,
                    "detail": f"HTTP {resp.status_code}",
                }
            except Exception as exc:
                results[name] = {
                    "status": "down",
                    "latency_ms": int((time.perf_counter() - s) * 1000),
                    "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
                }

        for name, url in [
            ("chatwoot", f"{settings.chatwoot_base_url}/health"),
            ("supabase", f"{settings.supabase_url}/auth/v1/health"),
            ("n8n", f"{settings.n8n_base_url}/healthz"),
        ]:
            s = time.perf_counter()
            try:
                if not url.split("/healthz")[0] and name == "n8n":
                    results[name] = {
                        "status": "down",
                        "latency_ms": int((time.perf_counter() - s) * 1000),
                        "detail": f"missing URL config: {settings.n8n_base_url}",
                    }
                    continue
                resp = await client.get(url)
                elapsed_ms = int((time.perf_counter() - s) * 1000)
                ok = resp.status_code in (200, 201, 401, 403, 405)
                results[name] = {
                    "status": "up" if ok else "down",
                    "latency_ms": elapsed_ms,
                    "detail": f"HTTP {resp.status_code}",
                }
            except Exception as exc:
                results[name] = {
                    "status": "down",
                    "latency_ms": int((time.perf_counter() - s) * 1000),
                    "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
                }

    return results


async def _check_dns_category() -> dict[str, dict[str, Any]]:
    """DNS checks em paralelo (asyncio.gather).

    Returns:
        Dict dominio -> status dict.
    """
    coros = [_check_dns(d) for d in RADAR_DNS_DOMAINS]
    statuses = await asyncio.gather(*coros, return_exceptions=True)
    out: dict[str, dict[str, Any]] = {}
    for domain, status in zip(RADAR_DNS_DOMAINS, statuses, strict=True):
        if isinstance(status, BaseException):
            out[domain] = {
                "status": "down",
                "latency_ms": 0,
                "detail": f"gather exception: {type(status).__name__}: {str(status)[:120]}",
            }
        else:
            out[domain] = cast("dict[str, Any]", status)
    return out


async def _check_traefik_category() -> dict[str, dict[str, Any]]:
    """Traefik router checks em paralelo.

    Returns:
        Dict dominio -> status dict.
    """
    coros = [_check_traefik(d) for d in RADAR_TRAEFIK_DOMAINS]
    statuses = await asyncio.gather(*coros, return_exceptions=True)
    out: dict[str, dict[str, Any]] = {}
    for domain, status in zip(RADAR_TRAEFIK_DOMAINS, statuses, strict=True):
        if isinstance(status, Exception):
            out[domain] = {
                "status": "down",
                "latency_ms": 0,
                "detail": f"gather exception: {type(status).__name__}: {str(status)[:120]}",
            }
        else:
            out[domain] = cast("dict[str, Any]", status)
    return out


async def _check_ssh_category() -> dict[str, dict[str, Any]]:
    """SSH VPS Hostinger + Tailscale.

    Returns:
        Dict com chaves 'ssh_vps' e 'tailscale'.
    """
    ssh_vps, tailscale = await asyncio.gather(
        _check_socket(RADAR_SSH_HOST, RADAR_SSH_PORT),
        _check_socket(RADAR_TAILSCALE_HOST, RADAR_TAILSCALE_PORT),
    )
    return {"ssh_vps": ssh_vps, "tailscale": tailscale}


async def _check_disk_category() -> dict[str, dict[str, Any]]:
    """Disk space (sync, pois shutil.disk_usage e rapido)."""
    return {"docker_volumes": _check_disk(RADAR_DISK_PATH)}


async def _check_mcp_category() -> dict[str, dict[str, Any]]:
    """G8.07.T4 — inventário de tools MCP no radar (sync, fail-open)."""

    def _run() -> dict[str, Any]:
        from app.services.mcp_radar_status import build_mcp_radar

        return build_mcp_radar().to_dict()

    try:
        payload = await asyncio.to_thread(_run)
        return {"mcp_tools": payload}
    except Exception as exc:  # noqa: BLE001
        return {
            "mcp_tools": {
                "status": "warn",
                "latency_ms": 0,
                "detail": f"mcp radar error: {type(exc).__name__}",
                "tool_count": 0,
                "tools": [],
            }
        }


async def _check_openclaw_category() -> dict[str, dict[str, Any]]:
    """G8.04.T1 — status OpenClaw gateway no radar (sync probe, fail-open)."""

    def _run() -> dict[str, Any]:
        from app.services.openclaw_radar import build_openclaw_radar

        return build_openclaw_radar().to_dict()

    try:
        payload = await asyncio.to_thread(_run)
        return {"gateway": payload}
    except Exception as exc:  # noqa: BLE001
        return {
            "gateway": {
                "status": "warn",
                "latency_ms": 0,
                "detail": f"openclaw radar error: {type(exc).__name__}",
            }
        }


def _aggregate_overall(categories: dict[str, dict[str, dict[str, Any]]]) -> str:
    """Calcula status agregado.

    Regra:
    - Se QUALQUER check tem status "down" e eh health critical (database/redis) -> "red"
    - Caso contrario, se QUALQUER check tem status "down" -> "yellow"
    - Caso contrario, se QUALQUER check tem status "warn" -> "yellow"
    - Caso contrario -> "green"

    Args:
        categories: dict aninhado categoria -> {check_name -> {status, ...}}.

    Returns:
        "green" | "yellow" | "red".
    """
    critical_health = {"database", "redis"}
    has_critical_down = False
    has_any_down = False
    has_any_warn = False
    for category_name, checks in categories.items():
        for check_name, payload in checks.items():
            status = payload.get("status")
            if status == "down":
                has_any_down = True
                if category_name == "health" and check_name in critical_health:
                    has_critical_down = True
            elif status == "warn":
                has_any_warn = True
    if has_critical_down:
        return "red"
    if has_any_down:
        return "yellow"
    if has_any_warn:
        return "yellow"
    return "green"


@expanded_router.get(
    "/health/radar/expanded",
    tags=["Health"],
    summary="Health Radar expandido (F6 [P2] 2026-07-15)",
    description=(
        "Estende `/health/radar` com 5 categorias adicionais: DNS (10 dominios), "
        "Traefik routers (5 dominios), SSH VPS Hostinger, Tailscale SSH e "
        "Disk space em /var/lib/docker/volumes.\n\n"
        "Categorias: health, dns, traefik, ssh, tailscale, disk. Cada check "
        "retorna `{status: up|down|warn, latency_ms, detail}`. Falha em qualquer "
        "check NAO quebra o endpoint (fail-open).\n\n"
        "Status agregado: green (tudo up), yellow (algum warn ou down nao-critico), "
        "red (database ou redis down). Use em conjunto com N8N workflow #30 "
        "para alerting."
    ),
    response_description="JSON agregado com 6 categorias.",
)
async def health_radar_expanded() -> dict[str, Any]:
    """Coleta TUDO em paralelo e retorna o radar expandido."""
    health_coro = _check_health_category()
    dns_coro = _check_dns_category()
    traefik_coro = _check_traefik_category()
    ssh_coro = _check_ssh_category()
    disk_coro = _check_disk_category()
    mcp_coro = _check_mcp_category()
    openclaw_coro = _check_openclaw_category()

    health: Any
    dns: Any
    traefik: Any
    ssh: Any
    disk: Any
    mcp: Any
    openclaw: Any
    health, dns, traefik, ssh, disk, mcp, openclaw = await asyncio.gather(
        health_coro,
        dns_coro,
        traefik_coro,
        ssh_coro,
        disk_coro,
        mcp_coro,
        openclaw_coro,
        return_exceptions=True,
    )

    def _coerce(value: Any, fallback: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if isinstance(value, BaseException):
            logger.error("radar_expanded gather exception: %s", value)
            return fallback
        if isinstance(value, dict):
            return cast("dict[str, dict[str, Any]]", value)
        return fallback

    categories: dict[str, dict[str, dict[str, Any]]] = {
        "health": _coerce(health, {}),
        "dns": _coerce(dns, {}),
        "traefik": _coerce(traefik, {}),
        "ssh": _coerce(ssh, {}),
        "disk": _coerce(disk, {}),
        "mcp": _coerce(mcp, {}),
        "openclaw": _coerce(openclaw, {}),
    }

    overall = _aggregate_overall(categories)
    return {
        "status": overall,
        "categories": categories,
        "metadata": {
            "version": "0.6.0",
            "domain_count_dns": len(RADAR_DNS_DOMAINS),
            "domain_count_traefik": len(RADAR_TRAEFIK_DOMAINS),
            "ssh_host": RADAR_SSH_HOST,
            "tailscale_host": RADAR_TAILSCALE_HOST,
            "disk_path": RADAR_DISK_PATH,
            "backend_server": socket.gethostname(),
        },
    }