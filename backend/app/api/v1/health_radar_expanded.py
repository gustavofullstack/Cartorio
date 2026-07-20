"""Health Radar Expanded (F6 [P2] 2026-07-15 / G8.15.T4 2026-07-18).

Estende o radar existente (`/api/v1/health/radar`) com 5 categorias
adicionais de checks (DNS, Traefik routers, SSH VPS, Tailscale, Disk space)
+ categoria **redis_queues** (G8.15.T4) que mapeia saude das filas
operacionais Redis: idempotency keys, rate-limit buckets, locks, bot_mute,
sessions e DLQ depth.

Endpoint: GET /api/v1/health/radar/expanded

Categorias:
- health        : 7 servicos (database, redis, openclaw, chatwoot, supabase, n8n, evolution)
- dns           : 10 dominios do F4 SRE
- traefik       : routers HTTPS dos dominios (status_code 200/302/401/403 = UP; 404 + content-length 2901 = WARN router sem match)
- ssh           : porta SSH do VPS Hostinger (187.77.236.77:22) UP/DOWN
- tailscale     : porta SSH Tailscale (100.99.172.84:22) UP/DOWN
- disk          : espaco livre em /var/lib/docker/volumes (free GB)
- mcp           : inventário de tools MCP (G8.07.T4)
- openclaw      : status dedicado do gateway OpenClaw (G8.04.T1)
- redis_queues  : G8.15.T4 — saude das filas Redis (idempotency/rate_limit/
                  dlq/lock/bot_mute/session) — counts LGPD-safe (zero PII raw).

Cada check retorna:
{
  "status": "up" | "down" | "warn",
  "latency_ms": int,
  "detail": str
}

Falha em qualquer check NAO quebra o endpoint (fail-open).
Todas as verificacoes sao executadas em paralelo via asyncio.gather.

Squad cartorio-front / F6 [P2] / 2026-07-15.
G8.15.T4 Redis queue radar — Gustavo Almeida / 2026-07-18.
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

# G8.15.T4 — redis_queues category
#
# Cap defensivo para cada SCAN (anti-OOM): se um namespace ultrapassar este
# limite, paramos de incrementar o contador mas mantemos o endpoint rapido.
# Para diagnostico profundo (acima do cap), operator pode usar `redis-cli
# --scan --pattern '<prefix>*'` diretamente no VPS.
REDIS_SCAN_HARD_CAP: int = 50_000

# Contagem maxima de TTLs amostrados por prefixo (sondagem leve para detectar
# chaves "expiring soon" — drift/lock-presence). Apenas amostra, nao enumera
# TUDO. 256 eh mais que suficiente para identificar buckets ativos vs stale.
REDIS_TTL_SAMPLE_LIMIT: int = 256

# Limite (em segundos) para considerar um rate-limit bucket "expiring soon"
# (i.e., bucket prestes a expirar e abrir janela). Apenas heuristica de radar.
RATE_LIMIT_EXPIRING_SOON_SEC: int = 10

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


async def _check_socket(
    host: str, port: int, timeout: float = SSH_SOCKET_TIMEOUT
) -> dict[str, Any]:
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
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
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

    async def probe_http(
        client: httpx.AsyncClient,
        name: str,
        url: str | None,
        accepted_statuses: tuple[int, ...],
    ) -> tuple[str, dict[str, Any]]:
        """Sonda HTTP: resposta inesperada e degradacao, nao disponibilidade."""
        start = time.perf_counter()
        if not url:
            return name, {
                "status": "warn",
                "latency_ms": 0,
                "detail": "missing URL config; health cannot be verified",
            }
        try:
            response = await client.get(url)
        except Exception as exc:
            return name, {
                "status": "down",
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "detail": f"{type(exc).__name__}: {str(exc)[:120]}",
            }
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code in accepted_statuses:
            return name, {
                "status": "up",
                "latency_ms": elapsed_ms,
                "detail": f"HTTP {response.status_code}",
            }
        return name, {
            "status": "warn",
            "latency_ms": elapsed_ms,
            "detail": f"HTTP {response.status_code}; endpoint reachable but health is not confirmed",
        }

    probes = (
        ("openclaw", settings.openclaw_base_url, "/health", (200,)),
        ("evolution", settings.evolution_base_url, "/", (200,)),
        ("chatwoot", settings.chatwoot_base_url, "/health", (200, 201)),
        ("supabase", settings.supabase_url, "/rest/v1/", (200, 401)),
        ("n8n", settings.n8n_base_url, "/healthz", (200,)),
    )
    async with httpx.AsyncClient(timeout=3.0) as client:
        checked = await asyncio.gather(
            *(
                probe_http(client, name, f"{base_url}{path}" if base_url else None, accepted)
                for name, base_url, path, accepted in probes
            )
        )
    results.update(dict(checked))

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


# ============================================================================
# G8.15.T4 — redis_queues category (2026-07-18)
#
# Strategy:
#   - 1 PING (saude geral)
#   - 6 SCANs em paralelo (um por prefixo/namespace) com COUNT hint
#   - DLQ pending via DB SELECT COUNT(*) (a DLQ canonica vive no Postgres
#     outbox_message, NAO em Redis LIST — ver `app/services/dlq.py`)
#   - Zero PII raw em qualquer path (apenas contagens inteiras)
#   - Hard cap REDIS_SCAN_HARD_CAP por namespace para anti-OOM
#   - TTL amostrado em ate REDIS_TTL_SAMPLE_LIMIT chaves para detectar
#     "expiring soon" (rate-limit drift, lock-presence)
#   - Fail-open em qualquer erro: retorna warn sem 500
# ============================================================================


def _scan_count(
    redis_client: Any,
    pattern: str,
    *,
    hard_cap: int = REDIS_SCAN_HARD_CAP,
    sample_ttls: int = 0,
    expiring_soon_sec: int | None = None,
) -> tuple[int, int]:
    """Conta chaves via SCAN (production-safe). Opcionalmente amostra TTLs.

    Args:
        redis_client: redis.Redis (sync) instance.
        pattern: glob pattern (ex.: "cartorio:idem:*").
        hard_cap: para de incrementar ao atingir este limite (anti-OOM).
        sample_ttls: 0 = nao amostra TTL; >0 = amostra ate N chaves e
            retorna (count, sample_count_with_ttl_in_window).
        expiring_soon_sec: se sample_ttls>0 e este param setado, conta
            quantas chaves da amostra tem TTL <= este valor (>0).

    Returns:
        Tuple (count_capped, expiring_soon_count). expiring_soon_count
        eh 0 se sample_ttls==0.
    """
    count = 0
    soon = 0
    sampled = 0
    try:
        cursor = 0
        while True:
            cursor, batch = redis_client.scan(cursor=cursor, match=pattern, count=500)
            for k in batch:
                count += 1
                if count > hard_cap:
                    return count, soon
                if sample_ttls > 0 and sampled < sample_ttls:
                    try:
                        ttl = redis_client.ttl(k)
                        # ttl == -1 (sem TTL) e -2 (nao existe) ignorados
                        if expiring_soon_sec is not None and 0 < ttl <= expiring_soon_sec:
                            soon += 1
                        sampled += 1
                    except Exception:  # noqa: BLE001
                        sampled += 1
            if cursor == 0:
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_queues scan fail pattern=%s err=%s", pattern, exc)
        return count, soon
    return count, soon


def _check_redis_queues_sync(
    redis_url: str,
    *,
    scan_hard_cap: int = REDIS_SCAN_HARD_CAP,
    ttl_sample: int = REDIS_TTL_SAMPLE_LIMIT,
) -> dict[str, Any]:
    """Coleta snapshot das 6 filas Redis + DLQ DB (sync, thread offload).

    Args:
        redis_url: URL Redis (settings.redis_url).
        scan_hard_cap: cap defensivo por prefixo.
        ttl_sample: limite de amostragem TTL.

    Returns:
        Dict com chaves:
          - status (up|warn|down)
          - latency_ms (int)
          - detail (str)
          - queues (dict) — sub-categorias com contagens
          - pii_safe_labels (bool) — sempre True (sem PII raw)
    """
    start = time.perf_counter()
    queues: dict[str, dict[str, Any]] = {}
    redis_ok = False

    try:
        import redis as redis_sync

        r = redis_sync.from_url(redis_url, socket_timeout=2.0)
        r.ping()
        redis_ok = True
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": elapsed,
            "detail": f"redis offline: {type(exc).__name__}: {str(exc)[:120]}",
            "pii_safe_labels": True,
            "queues": {
                "idempotency_keys_pending": {"count": 0, "exhausted": False},
                "rate_limit_buckets_active": {
                    "count": 0,
                    "expiring_soon": 0,
                    "exhausted": False,
                },
                "dlq_messages_pending": {"count": 0, "source": "db_skipped"},
                "cartorio_lock_active": {"count": 0, "exhausted": False},
                "cartorio_bot_mute_active": {"count": 0, "exhausted": False},
                "cartorio_session_memory": {"count": 0, "exhausted": False},
            },
        }

    # 1. Idempotency keys (cartorio:idem:* + legacy idem:* + idempotency:*)
    idem_count = 0
    for pat in ("cartorio:idem:*", "idem:*", "idempotency:*"):
        c, _ = _scan_count(r, pat, hard_cap=scan_hard_cap)
        idem_count += c
        if idem_count > scan_hard_cap:
            break
    queues["idempotency_keys_pending"] = {
        "count": min(idem_count, scan_hard_cap),
        "exhausted": idem_count > scan_hard_cap,
    }

    # 2. Rate-limit buckets (TTL-amostrado para "expiring soon")
    rl_count = 0
    rl_soon = 0
    for pat in (
        "cartorio:rate_limit:*",
        "ratelimit:apikey:*",
        "ratelimit:ip:*",
        "sliding:ip:*",
    ):
        c, s = _scan_count(
            r,
            pat,
            hard_cap=scan_hard_cap,
            sample_ttls=ttl_sample,
            expiring_soon_sec=RATE_LIMIT_EXPIRING_SOON_SEC,
        )
        rl_count += c
        rl_soon += s
        if rl_count > scan_hard_cap:
            break
    queues["rate_limit_buckets_active"] = {
        "count": min(rl_count, scan_hard_cap),
        "expiring_soon": rl_soon,
        "exhausted": rl_count > scan_hard_cap,
    }

    # 3. DLQ pending — fonte canonica eh Postgres outbox_message (ver dlq.py)
    # Fallback gracioso se DB indisponivel.
    dlq_count = 0
    dlq_source = "db_outbox_message"
    try:
        from app.db import SessionLocal  # local import para evitar ciclo
        from app.models.outbox_message import OutboxMessage, OutboxStatus

        with SessionLocal() as session:
            dlq_count = (
                session.query(OutboxMessage)
                .filter(OutboxMessage.status == OutboxStatus.PENDING)
                .count()
            )
    except Exception as exc:  # noqa: BLE001
        dlq_source = "db_error"
        logger.warning(
            "redis_queues dlq db query failed: %s: %s",
            type(exc).__name__,
            str(exc)[:120],
        )
    queues["dlq_messages_pending"] = {"count": dlq_count, "source": dlq_source}

    # 4. Redlock ativos (cartorio:lock:* + legacy redlock:*)
    lock_count = 0
    for pat in ("cartorio:lock:*", "redlock:*"):
        c, _ = _scan_count(r, pat, hard_cap=scan_hard_cap)
        lock_count += c
        if lock_count > scan_hard_cap:
            break
    queues["cartorio_lock_active"] = {
        "count": min(lock_count, scan_hard_cap),
        "exhausted": lock_count > scan_hard_cap,
    }

    # 5. Bot mute ativos (HITL)
    mute_count = 0
    for pat in ("cartorio:bot_mute:*", "bot:mute:*"):
        c, _ = _scan_count(r, pat, hard_cap=scan_hard_cap)
        mute_count += c
        if mute_count > scan_hard_cap:
            break
    queues["cartorio_bot_mute_active"] = {
        "count": min(mute_count, scan_hard_cap),
        "exhausted": mute_count > scan_hard_cap,
    }

    # 6. Sessions em memoria (chat memory curta + session canonica)
    sess_count = 0
    for pat in ("cartorio:session:*", "cartorio:sess:*"):
        c, _ = _scan_count(r, pat, hard_cap=scan_hard_cap)
        sess_count += c
        if sess_count > scan_hard_cap:
            break
    queues["cartorio_session_memory"] = {
        "count": min(sess_count, scan_hard_cap),
        "exhausted": sess_count > scan_hard_cap,
    }

    elapsed = int((time.perf_counter() - start) * 1000)
    exhausted_count = sum(1 for q in queues.values() if isinstance(q, dict) and q.get("exhausted"))

    # Status logico:
    # - down: redis offline (early-return acima)
    # - warn: >=1 namespace estourou o cap (sinal de saturação)
    # - up: tudo dentro do cap
    if not redis_ok:
        status = "down"
        detail = "redis offline"
    elif exhausted_count > 0:
        status = "warn"
        detail = (
            f"{exhausted_count} namespace(s) excederam cap={scan_hard_cap} (saturacao provavel)"
        )
    else:
        status = "up"
        detail = f"6 namespaces scanned em {elapsed}ms"

    return {
        "status": status,
        "latency_ms": elapsed,
        "detail": detail,
        "pii_safe_labels": True,
        "queues": queues,
    }


async def _check_redis_queues_category() -> dict[str, dict[str, Any]]:
    """G8.15.T4 — radar das filas Redis (sync probe via asyncio.to_thread)."""

    def _run() -> dict[str, Any]:
        return _check_redis_queues_sync(settings.redis_url)

    try:
        payload = await asyncio.to_thread(_run)
        return {"redis_queues": payload}
    except Exception as exc:  # noqa: BLE001
        return {
            "redis_queues": {
                "status": "warn",
                "latency_ms": 0,
                "detail": f"redis_queues radar error: {type(exc).__name__}",
                "pii_safe_labels": True,
                "queues": {},
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
    summary="Health Radar expandido (F6 [P2] 2026-07-15 + G8.15.T4 2026-07-18)",
    description=(
        "Estende `/health/radar` com 5 categorias adicionais: DNS (10 dominios), "
        "Traefik routers (5 dominios), SSH VPS Hostinger, Tailscale SSH e "
        "Disk space em /var/lib/docker/volumes. **G8.15.T4** adiciona a categoria "
        "`redis_queues` com snapshot de 6 namespaces (idempotency, rate_limit, "
        "dlq via DB outbox_message, lock, bot_mute, session) — contagens LGPD-safe "
        "(zero PII raw, apenas inteiros).\n\n"
        "Categorias: health, dns, traefik, ssh, tailscale, disk, mcp, openclaw, "
        "redis_queues. Cada check retorna `{status: up|down|warn, latency_ms, "
        "detail}`. Falha em qualquer check NAO quebra o endpoint (fail-open).\n\n"
        "Status agregado: green (tudo up), yellow (algum warn ou down nao-critico), "
        "red (database ou redis down). Use em conjunto com N8N workflow #30 "
        "para alerting."
    ),
    response_description="JSON agregado com 9 categorias (health + 8 auxiliares).",
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
    redis_queues_coro = _check_redis_queues_category()

    health: Any
    dns: Any
    traefik: Any
    ssh: Any
    disk: Any
    mcp: Any
    openclaw: Any
    redis_queues: Any
    health, dns, traefik, ssh, disk, mcp, openclaw, redis_queues = await asyncio.gather(
        health_coro,
        dns_coro,
        traefik_coro,
        ssh_coro,
        disk_coro,
        mcp_coro,
        openclaw_coro,
        redis_queues_coro,
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
        "redis_queues": _coerce(redis_queues, {}),
    }

    overall = _aggregate_overall(categories)
    return {
        "status": overall,
        "categories": categories,
        "metadata": {
            "version": "0.6.1",
            "domain_count_dns": len(RADAR_DNS_DOMAINS),
            "domain_count_traefik": len(RADAR_TRAEFIK_DOMAINS),
            "ssh_host": RADAR_SSH_HOST,
            "tailscale_host": RADAR_TAILSCALE_HOST,
            "disk_path": RADAR_DISK_PATH,
            "backend_server": socket.gethostname(),
            "redis_scan_hard_cap": REDIS_SCAN_HARD_CAP,
            "redis_ttl_sample_limit": REDIS_TTL_SAMPLE_LIMIT,
            "rate_limit_expiring_soon_sec": RATE_LIMIT_EXPIRING_SOON_SEC,
        },
    }
