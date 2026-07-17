"""G8.09.T1 — Probe de latência TCP interna via Tailscale.

Complementa `health_radar_expanded` (RADAR_TAILSCALE_HOST=100.99.172.84:22)
com um serviço dedicado, testável e invocável via CLI:

  python -m app.services.tailscale_probe

API:
- TailscaleProbeResult — resultado de um host:port
- probe_tcp(host, port, timeout=2.0) — socket puro (create_connection)
- probe_tailscale_defaults() — hosts canônicos (env-overridable)
- format_report(results) — markdown operacional

Hosts default:
- VPS mesh SSH: 100.99.172.84:22 (RADAR_TAILSCALE_HOST / PORT)
- API interna opcional: TAILSCALE_API_HOST:TAILSCALE_API_PORT se definidos

Modified by Gustavo Almeida — G8 Wave 37 Squad 09.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from dataclasses import asdict, dataclass
from typing import Sequence


# Alinhado com health_radar_expanded.RADAR_TAILSCALE_*
DEFAULT_TAILSCALE_HOST: str = "100.99.172.84"
DEFAULT_TAILSCALE_PORT: int = 22
DEFAULT_TIMEOUT_SEC: float = 2.0


@dataclass(frozen=True, slots=True)
class TailscaleProbeResult:
    """Resultado de um probe TCP em host:port na mesh Tailscale."""

    host: str
    port: int
    ok: bool
    latency_ms: float
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def probe_tcp(
    host: str,
    port: int,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> TailscaleProbeResult:
    """TCP connect probe (socket.create_connection). Pure — sem asyncio.

    Args:
        host: hostname ou IP (ex.: 100.99.172.84).
        port: porta TCP (ex.: 22).
        timeout: timeout em segundos.

    Returns:
        TailscaleProbeResult com ok, latency_ms e detail.
    """
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return TailscaleProbeResult(
                host=host,
                port=port,
                ok=True,
                latency_ms=round(elapsed_ms, 3),
                detail=f"TCP connect OK {host}:{port}",
            )
    except TimeoutError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return TailscaleProbeResult(
            host=host,
            port=port,
            ok=False,
            latency_ms=round(elapsed_ms, 3),
            detail=f"TimeoutError: {exc or f'timed out after {timeout}s'}",
        )
    except OSError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return TailscaleProbeResult(
            host=host,
            port=port,
            ok=False,
            latency_ms=round(elapsed_ms, 3),
            detail=f"{type(exc).__name__}: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 — fail-open probe
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return TailscaleProbeResult(
            host=host,
            port=port,
            ok=False,
            latency_ms=round(elapsed_ms, 3),
            detail=f"{type(exc).__name__}: {str(exc)[:200]}",
        )


def _default_targets() -> list[tuple[str, int]]:
    """Resolve lista de (host, port) a partir de env + defaults canônicos."""
    host = os.environ.get("RADAR_TAILSCALE_HOST", DEFAULT_TAILSCALE_HOST).strip()
    port_raw = os.environ.get("RADAR_TAILSCALE_PORT", str(DEFAULT_TAILSCALE_PORT)).strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = DEFAULT_TAILSCALE_PORT

    targets: list[tuple[str, int]] = [(host, port)]

    api_host = os.environ.get("TAILSCALE_API_HOST", "").strip()
    if api_host:
        api_port_raw = os.environ.get("TAILSCALE_API_PORT", "8000").strip()
        try:
            api_port = int(api_port_raw)
        except ValueError:
            api_port = 8000
        if (api_host, api_port) not in targets:
            targets.append((api_host, api_port))

    return targets


def probe_tailscale_defaults(
    timeout: float = DEFAULT_TIMEOUT_SEC,
    targets: Sequence[tuple[str, int]] | None = None,
) -> list[TailscaleProbeResult]:
    """Probe dos hosts Tailscale conhecidos (default 100.99.172.84:22).

    Env:
        RADAR_TAILSCALE_HOST / RADAR_TAILSCALE_PORT — override do default SSH
        TAILSCALE_API_HOST / TAILSCALE_API_PORT — host API interno opcional

    Args:
        timeout: timeout por host.
        targets: lista opcional de (host, port); se None, usa defaults/env.

    Returns:
        Lista de TailscaleProbeResult (ordem estável).
    """
    resolved = list(targets) if targets is not None else _default_targets()
    return [probe_tcp(h, p, timeout=timeout) for h, p in resolved]


def format_report(results: Sequence[TailscaleProbeResult]) -> str:
    """Renderiza relatório markdown dos probes.

    Args:
        results: resultados de probe_tcp / probe_tailscale_defaults.

    Returns:
        String markdown não-vazia com tabela e sumário.
    """
    lines: list[str] = [
        "# Tailscale internal latency probe (G8.09.T1)",
        "",
        f"Probes: **{len(results)}**",
        "",
        "| Host | Port | OK | Latency (ms) | Detail |",
        "| --- | ---: | :---: | ---: | --- |",
    ]
    ok_count = 0
    for r in results:
        if r.ok:
            ok_count += 1
        flag = "yes" if r.ok else "no"
        detail = r.detail.replace("|", "\\|")
        lines.append(
            f"| `{r.host}` | {r.port} | {flag} | {r.latency_ms:.3f} | {detail} |"
        )

    fail_count = len(results) - ok_count
    status = "GREEN" if fail_count == 0 and results else ("YELLOW" if ok_count else "RED")
    lines.extend(
        [
            "",
            f"**Summary:** {ok_count}/{len(results)} OK — status **{status}**",
            "",
            "_Socket TCP connect only (no SSH auth). Aligns with "
            "`health_radar_expanded` RADAR_TAILSCALE_HOST._",
            "",
        ]
    )
    return "\n".join(lines)


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.tailscale_probe",
        description="Probe de latência TCP na mesh Tailscale (G8.09.T1).",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"Host único (default env/radar: {DEFAULT_TAILSCALE_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Porta (default: {DEFAULT_TAILSCALE_PORT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SEC,
        help=f"Timeout em segundos (default: {DEFAULT_TIMEOUT_SEC})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída JSON em vez de markdown",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.host is not None:
        port = args.port if args.port is not None else DEFAULT_TAILSCALE_PORT
        results = [probe_tcp(args.host, port, timeout=args.timeout)]
    else:
        results = probe_tailscale_defaults(timeout=args.timeout)

    if args.json:
        import json

        print(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
    else:
        print(format_report(results))

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(_cli())
