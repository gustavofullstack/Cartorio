#!/usr/bin/env python3
"""Parse Traefik access logs and extract backend (ServiceName) for 502 debug.

G7.13.T2 — offline-friendly helper for cartorio-sre on-call.

Usage:
  python3 scripts/traefik_access_log_parse.py --demo
  python3 scripts/traefik_access_log_parse.py access.jsonl --filter-status 502
  docker service logs easypanel-traefik --tail 200 --no-trunc 2>&1 \\
    | python3 scripts/traefik_access_log_parse.py --summary

No network calls. No secrets. Safe for CI/local.

Modified by Gustavo Almeida — G7 Wave 27
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO

# Traefik EasyPanel pattern: http-cartorio_api-0@file
BACKEND_RE = re.compile(
    r"(?P<backend>(?:https?)-[\w.-]+(?:-\d+)?@(?:file|docker|consulcatalog|ecs))",
    re.IGNORECASE,
)
# Loose CLF-ish status near end of line
STATUS_RE = re.compile(r"\b(?P<status>[1-5]\d{2})\b")
HOST_RE = re.compile(
    r"(?:RequestHost|Host)[\"']?\s*[:=]\s*[\"']?(?P<host>[\w.-]+\.[\w.-]+)",
    re.IGNORECASE,
)

DEMO_LINES = [
    # JSON samples (shape aproximado Traefik accessLog format=json)
    json.dumps(
        {
            "ClientAddr": "203.0.113.10:51234",
            "RequestHost": "chat.2notasudi.com.br",
            "RequestMethod": "GET",
            "RequestPath": "/",
            "DownstreamStatus": 502,
            "OriginStatus": 0,
            "ServiceName": "http-cartorio_chatwoot-0@file",
            "RouterName": "http-cartorio_chatwoot@file",
            "Duration": 52_000_000,
        }
    ),
    json.dumps(
        {
            "ClientAddr": "203.0.113.11:44321",
            "RequestHost": "whatsapp.2notasudi.com.br",
            "RequestMethod": "GET",
            "RequestPath": "/",
            "DownstreamStatus": 502,
            "OriginStatus": 0,
            "ServiceName": "http-cartorio_evolution-api-0@file",
            "RouterName": "http-cartorio_evolution-api@file",
            "Duration": 48_000_000,
        }
    ),
    json.dumps(
        {
            "ClientAddr": "203.0.113.12:40001",
            "RequestHost": "api.2notasudi.com.br",
            "RequestMethod": "GET",
            "RequestPath": "/health",
            "DownstreamStatus": 200,
            "OriginStatus": 200,
            "ServiceName": "http-cartorio_api-0@file",
            "RouterName": "http-cartorio_api@file",
            "Duration": 3_200_000,
        }
    ),
    # Text / mixed line (fallback path)
    (
        "2026-07-14T13:42:00Z GET https://flow.2notasudi.com.br/ "
        "http-cartorio_n8n-0@file 502 74ms"
    ),
    (
        "2026-07-14T13:42:01Z GET https://supbase.2notasudi.com.br/ "
        "https-cartorio_supabase-1@file 404 12ms"
    ),
]


@dataclass(frozen=True)
class AccessHit:
    backend: str
    host: str
    method: str
    path: str
    status: int | None
    raw_preview: str


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_json_line(line: str) -> AccessHit | None:
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    backend = (
        data.get("ServiceName")
        or data.get("service")
        or data.get("BackendName")
        or data.get("backend")
        or ""
    )
    if not backend:
        # sometimes nested
        svc = data.get("Service") or {}
        if isinstance(svc, dict):
            backend = str(svc.get("Name") or svc.get("name") or "")
    if not backend:
        m = BACKEND_RE.search(line)
        backend = m.group("backend") if m else "unknown"

    host = str(
        data.get("RequestHost") or data.get("Host") or data.get("request_Host") or "?"
    )
    method = str(data.get("RequestMethod") or data.get("Method") or "?")
    path = str(
        data.get("RequestPath") or data.get("RequestUri") or data.get("Uri") or "?"
    )
    status = _as_int(
        data.get("DownstreamStatus")
        if data.get("DownstreamStatus") is not None
        else data.get("OriginStatus")
        if data.get("OriginStatus") is not None
        else data.get("StatusCode")
    )
    return AccessHit(
        backend=str(backend),
        host=host,
        method=method,
        path=path,
        status=status,
        raw_preview=line[:160],
    )


def parse_text_line(line: str) -> AccessHit | None:
    line = line.strip()
    if not line:
        return None
    m_back = BACKEND_RE.search(line)
    if not m_back:
        return None
    backend = m_back.group("backend")
    m_host = HOST_RE.search(line)
    host = m_host.group("host") if m_host else "?"
    # Host often appears as https://host/ in text logs
    if host == "?":
        m_url = re.search(r"https?://(?P<h>[\w.-]+)", line)
        if m_url:
            host = m_url.group("h")
    statuses = [int(x) for x in STATUS_RE.findall(line)]
    # Prefer last 3xx/4xx/5xx as response status
    status: int | None = None
    for s in reversed(statuses):
        if 100 <= s <= 599:
            status = s
            break
    method = "?"
    for candidate in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        if re.search(rf"\b{candidate}\b", line):
            method = candidate
            break
    path = "?"
    m_path = re.search(r"https?://[\w.-]+(?P<p>/[^\s\"]*)", line)
    if m_path:
        path = m_path.group("p") or "/"
    return AccessHit(
        backend=backend,
        host=host,
        method=method,
        path=path,
        status=status,
        raw_preview=line[:160],
    )


def parse_line(line: str) -> AccessHit | None:
    hit = parse_json_line(line)
    if hit is not None:
        return hit
    return parse_text_line(line)


def iter_lines(sources: Iterable[str | Path | TextIO]) -> Iterator[str]:
    for src in sources:
        if hasattr(src, "read"):
            for line in src:  # type: ignore[union-attr]
                yield line
            continue
        path = Path(str(src))
        if str(src) == "-":
            for line in sys.stdin:
                yield line
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        yield from text.splitlines()


def filter_hits(
    hits: Iterable[AccessHit],
    *,
    status: int | None,
    backend_substr: str | None,
    host_substr: str | None,
) -> list[AccessHit]:
    out: list[AccessHit] = []
    for h in hits:
        if status is not None and h.status != status:
            continue
        if backend_substr and backend_substr.lower() not in h.backend.lower():
            continue
        if host_substr and host_substr.lower() not in h.host.lower():
            continue
        out.append(h)
    return out


def print_table(hits: list[AccessHit]) -> None:
    if not hits:
        print("No matching access log lines.")
        return
    # backend | host | status | method path
    print(f"{'BACKEND':<42} {'HOST':<28} {'ST':>3}  METHOD PATH")
    print("-" * 100)
    for h in hits:
        st = str(h.status) if h.status is not None else "?"
        print(f"{h.backend:<42} {h.host:<28} {st:>3}  {h.method} {h.path}")


def print_summary(hits: list[AccessHit]) -> None:
    if not hits:
        print("No matching access log lines.")
        return
    by_backend = Counter(h.backend for h in hits)
    by_status = Counter(h.status for h in hits)
    by_host = Counter(h.host for h in hits)
    print("=== Summary by backend ===")
    for name, n in by_backend.most_common():
        print(f"  {n:5d}  {name}")
    print("=== Summary by status ===")
    for st, n in sorted(by_status.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {n:5d}  {st}")
    print("=== Summary by host (top 15) ===")
    for host, n in by_host.most_common(15):
        print(f"  {n:5d}  {host}")
    # Common 502 mapping hint
    print("=== Hint (502 mapping) ===")
    for h in hits:
        if h.status != 502:
            continue
        if "chatwoot" in h.backend:
            print(
                "  chatwoot 502 → check cartorio_chatwoot replicas + DB env (Lesson 176)"
            )
            break
    for h in hits:
        if h.status == 502 and "evolution" in h.backend:
            print("  evolution 502 → check cartorio_evolution-api + Prisma/DB host")
            break
    for h in hits:
        if h.status == 502 and "n8n" in h.backend:
            print("  n8n 502 → check cartorio_n8n DB credentials / crashloop")
            break


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parse Traefik access logs → backend name (G7.13.T2)",
    )
    p.add_argument(
        "files",
        nargs="*",
        help="Log files (JSONL or text). Use '-' or omit for stdin when not --demo.",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Parse built-in sample lines (offline, no files needed).",
    )
    p.add_argument(
        "--filter-status",
        type=int,
        default=None,
        metavar="CODE",
        help="Keep only this Downstream/HTTP status (e.g. 502).",
    )
    p.add_argument(
        "--filter-backend",
        default=None,
        metavar="SUBSTR",
        help="Substring match on backend/ServiceName.",
    )
    p.add_argument(
        "--filter-host",
        default=None,
        metavar="SUBSTR",
        help="Substring match on RequestHost.",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Print counters instead of full table.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    raw_lines: list[str]
    if args.demo:
        raw_lines = list(DEMO_LINES)
    elif args.files:
        raw_lines = list(iter_lines(args.files))
    elif not sys.stdin.isatty():
        raw_lines = list(sys.stdin)
    else:
        build_parser().print_help()
        print("\nTip: use --demo for offline samples.", file=sys.stderr)
        return 2

    hits: list[AccessHit] = []
    for line in raw_lines:
        # docker service logs prefix: service.1.xxx@node | {json}
        if " | " in line and line.strip().endswith("}") is False:
            # strip docker log prefix when present
            parts = line.split(" | ", 1)
            if len(parts) == 2 and (
                parts[1].lstrip().startswith("{") or "@file" in parts[1]
            ):
                line = parts[1]
        hit = parse_line(line)
        if hit is not None:
            hits.append(hit)

    hits = filter_hits(
        hits,
        status=args.filter_status,
        backend_substr=args.filter_backend,
        host_substr=args.filter_host,
    )

    if args.summary or args.demo:
        if args.demo and not args.summary:
            print("=== Demo table (sample fixtures) ===")
            print_table(hits)
            print()
        print_summary(hits)
    else:
        print_table(hits)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
