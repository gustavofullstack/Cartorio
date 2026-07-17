"""G8.04.T1 — Status OpenClaw para o painel de radar expandido.

Probe HTTP curto (HEAD/GET) em `/health` do gateway OpenClaw + inventário
opcional de config local. Fail-open: offline → `warn` (não quebra o radar).

Retorna payload pronto para `/api/v1/health/radar/expanded` categories['openclaw'].

Modified by Gustavo Almeida — G8.04.T1 Wave 32.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# Public Traefik front for OpenClaw gateway (prod).
DEFAULT_OPENCLAW_PUBLIC_BASE = 'https://agent.2notasudi.com.br'
# Docker Swarm internal default (also in settings.openclaw_base_url).
DEFAULT_OPENCLAW_INTERNAL_BASE = 'http://cartorio_openclaw-gateway:18789'
OPENCLAW_PROBE_TIMEOUT_S = 2.0
# Candidate local config paths (VPS container mount + common host paths).
DEFAULT_CONFIG_CANDIDATES: tuple[Path, ...] = (
    Path('/home/node/.openclaw/openclaw.json'),
    Path('/home/node/.openclaw/agents/main/agent/agent.json'),
    Path.home() / '.openclaw' / 'openclaw.json',
)


@dataclass(slots=True)
class OpenClawRadarReport:
    status: str  # up | down | warn
    latency_ms: int = 0
    detail: str = ''
    url: str = ''
    http_status: int | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            'status': self.status,
            'latency_ms': self.latency_ms,
            'detail': self.detail,
            'url': self.url,
        }
        if self.http_status is not None:
            out['http_status'] = self.http_status
        if self.config:
            out['config'] = self.config
        return out


def _resolve_base_url(base_url: str | None = None) -> str:
    """Resolve base URL: explicit → settings → public agent domain."""
    if base_url and base_url.strip():
        return base_url.strip().rstrip('/')
    try:
        from app.config import settings

        configured = (settings.openclaw_base_url or '').strip()
        if configured:
            return configured.rstrip('/')
    except Exception:  # noqa: BLE001 — settings may be unavailable in pure unit paths
        pass
    return DEFAULT_OPENCLAW_PUBLIC_BASE


def inventory_openclaw_config(config_path: Path | None = None) -> dict[str, Any]:
    """Inventário opcional de config local (sem ler secrets).

    Só reporta existência/tamanho/nome — nunca conteúdo (tokens, keys).
    """
    candidates: list[Path]
    if config_path is not None:
        candidates = [config_path]
    else:
        candidates = list(DEFAULT_CONFIG_CANDIDATES)

    for path in candidates:
        try:
            if path.is_file():
                try:
                    size = path.stat().st_size
                except OSError:
                    size = -1
                return {
                    'present': True,
                    'path': path.name,  # basename only — no full host path leak of home
                    'bytes': size,
                }
        except OSError:
            continue
    return {'present': False}


def _probe_health(health_url: str, timeout_s: float = OPENCLAW_PROBE_TIMEOUT_S) -> tuple[str, str, int | None]:
    """HEAD then GET fallback. Offline → warn (fail-open)."""
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True, verify=True) as client:
            try:
                resp = client.head(health_url)
                # Some gateways reject HEAD with 405 — fall through to GET.
                if resp.status_code == 405:
                    resp = client.get(health_url)
            except httpx.HTTPError:
                resp = client.get(health_url)

            code = resp.status_code
            # Alive if health OK or auth-gated (gateway up, needs token).
            if code in (200, 201, 204, 401, 403, 405):
                return 'up', f'HTTP {code}', code
            if 500 <= code < 600:
                return 'warn', f'HTTP {code} (gateway error)', code
            return 'warn', f'HTTP {code}', code
    except httpx.TimeoutException:
        return 'warn', f'timeout (>{timeout_s}s)', None
    except httpx.ConnectError as exc:
        # Offline / DNS / connection refused — fail-open warn.
        return 'warn', f'offline: {type(exc).__name__}', None
    except httpx.HTTPError as exc:
        return 'warn', f'{type(exc).__name__}: {str(exc)[:100]}', None
    except Exception as exc:  # noqa: BLE001
        return 'warn', f'{type(exc).__name__}: {str(exc)[:100]}', None


def build_openclaw_radar(
    base_url: str | None = None,
    *,
    config_path: Path | None = None,
    timeout_s: float = OPENCLAW_PROBE_TIMEOUT_S,
    skip_probe: bool = False,
) -> OpenClawRadarReport:
    """Monta report de radar do OpenClaw.

    Args:
        base_url: override (settings / public agent se omitido).
        config_path: path opcional de config local a inventariar.
        timeout_s: timeout HTTP curto.
        skip_probe: se True, só inventaria config (path offline unit tests).

    Returns:
        OpenClawRadarReport (status/latency_ms/detail + extras).
    """
    start = time.perf_counter()
    resolved = _resolve_base_url(base_url)
    health_url = f'{resolved}/health'
    config_info = inventory_openclaw_config(config_path)

    if skip_probe:
        status = 'warn'
        detail = 'probe skipped'
        http_status: int | None = None
    else:
        status, detail, http_status = _probe_health(health_url, timeout_s=timeout_s)

    if config_info.get('present'):
        detail = f'{detail}; config={config_info.get("path")}'
    else:
        detail = f'{detail}; config=absent'

    elapsed = int((time.perf_counter() - start) * 1000)
    return OpenClawRadarReport(
        status=status,
        latency_ms=elapsed,
        detail=detail,
        url=health_url,
        http_status=http_status,
        config=config_info,
    )


__all__ = [
    'DEFAULT_CONFIG_CANDIDATES',
    'DEFAULT_OPENCLAW_INTERNAL_BASE',
    'DEFAULT_OPENCLAW_PUBLIC_BASE',
    'OPENCLAW_PROBE_TIMEOUT_S',
    'OpenClawRadarReport',
    'build_openclaw_radar',
    'inventory_openclaw_config',
]
