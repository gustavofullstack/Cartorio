#!/usr/bin/env python3
"""Safe, read-only smoke test for the Cartório AI agent route.

The smoke intentionally never authenticates to OpenClaw and never sends a chat
message.  It is therefore safe to run against the EasyPanel test hostname or
the future branded DNS name without risking PII entering an LLM/provider log.

Checks:
* OpenClaw liveness (HTTP only);
* LobeChat health through the EasyPanel proxy and, optionally, branded DNS;
* browser CORS preflight from LobeChat to OpenClaw;
* WebSocket connection challenge only (no auth response and no message body).

Usage:
    python3 scripts/smoke_cartorio_agent.py
    python3 scripts/smoke_cartorio_agent.py --strict-canonical --json

Exit codes: 0 healthy, 1 an essential check failed, 2 invalid local setup.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

import httpx

DEFAULT_AGENT_URL = "https://agent.2notasudi.com.br"
# This is the currently reachable EasyPanel wildcard route. It is a test/
# transitional hostname, not the public canonical name.
DEFAULT_EASYPANEL_LOBE_URL = "https://cartorio-lobechat.dfgdxq.easypanel.host"
# Desired canonical hostname. DNS/Traefik is deliberately not assumed ready.
DEFAULT_CANONICAL_LOBE_URL = "https://lobe.2notasudi.com.br"
TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ProbeResult:
    """A redacted probe outcome; never contains response bodies or credentials."""

    name: str
    status: str  # ok | warn | error
    details: str


def _join(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _safe_error(exc: Exception) -> str:
    """Return a bounded error category without echoing URLs, headers, or bodies."""
    return type(exc).__name__


def check_agent_health(agent_url: str) -> ProbeResult:
    """Probe the unauthenticated liveness endpoint; response body is discarded."""
    try:
        response = httpx.get(_join(agent_url, "/health"), timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return ProbeResult("openclaw_health", "error", f"request failed: {_safe_error(exc)}")
    status = "ok" if response.status_code == 200 else "error"
    return ProbeResult("openclaw_health", status, f"HTTP {response.status_code}")


def check_lobechat_proxy(name: str, lobe_url: str, *, optional: bool) -> ProbeResult:
    """Probe public LobeChat without following it into an authenticated chat flow."""
    # /api/health is the container's preferred route. Some EasyPanel proxy
    # versions expose /health instead; accepting it preserves a useful read-only
    # smoke while making the fallback explicit in output.
    for path in ("/api/health", "/health"):
        try:
            response = httpx.get(_join(lobe_url, path), timeout=TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            last_error = _safe_error(exc)
            continue
        if response.status_code == 200:
            detail = f"HTTP 200 path={path}"
            if path != "/api/health":
                detail += " (proxy fallback)"
            return ProbeResult(name, "ok", detail)
        last_error = f"HTTP {response.status_code} path={path}"

    return ProbeResult(name, "warn" if optional else "error", f"unhealthy: {last_error}")


def check_cors(agent_url: str, origin: str) -> ProbeResult:
    """Run a credential-free browser preflight; no chat request is made."""
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    try:
        response = httpx.options(
            _join(agent_url, "/v1/chat/completions"), headers=headers, timeout=TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return ProbeResult("openclaw_cors", "error", f"preflight failed: {_safe_error(exc)}")

    allowed_origin = response.headers.get("access-control-allow-origin")
    allowed = allowed_origin in {origin, "*"}
    if 200 <= response.status_code < 300 and allowed:
        return ProbeResult("openclaw_cors", "ok", f"HTTP {response.status_code}; origin allowed")
    # Do not include returned header values: proxies can reflect unexpected data.
    return ProbeResult(
        "openclaw_cors",
        "error",
        f"HTTP {response.status_code}; origin {'allowed' if allowed else 'not allowed'}",
    )


async def check_websocket_challenge(agent_url: str, origin: str) -> ProbeResult:
    """Open a WS and observe only the initial server challenge, then close.

    The client sends neither ``auth.challenge`` nor a chat message. This proves
    TLS/proxy upgrade and the gateway's challenge behaviour without requiring a
    token/password or processing personal data.
    """
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        return ProbeResult("openclaw_ws_challenge", "error", "websockets dependency unavailable")

    ws_url = _join(agent_url.replace("https://", "wss://").replace("http://", "ws://"), "/v1/chat")
    try:
        async with websockets.connect(ws_url, origin=origin, open_timeout=TIMEOUT_SECONDS) as websocket:
            raw = await asyncio.wait_for(websocket.recv(), timeout=TIMEOUT_SECONDS)
    except Exception as exc:  # library exposes several version-specific exception types
        return ProbeResult("openclaw_ws_challenge", "error", f"upgrade/challenge failed: {_safe_error(exc)}")

    try:
        event = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return ProbeResult("openclaw_ws_challenge", "error", "first server frame is not JSON")
    if event.get("type") == "event" and event.get("event") == "connect.challenge":
        return ProbeResult("openclaw_ws_challenge", "ok", "connected; connect.challenge received")
    # Intentionally identify only the schema shape, never serialise the frame.
    return ProbeResult("openclaw_ws_challenge", "error", "unexpected first server event")


def _hostname(url: str) -> str:
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("URL must include a hostname")
    return hostname


def check_dns_target(canonical_url: str) -> ProbeResult:
    """Give a clear DNS signal before the optional canonical proxy probe."""
    try:
        socket.getaddrinfo(_hostname(canonical_url), 443, type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return ProbeResult("canonical_dns", "warn", "hostname does not resolve")
    return ProbeResult("canonical_dns", "ok", "hostname resolves")


def run_smoke(
    *,
    agent_url: str = DEFAULT_AGENT_URL,
    easypanel_lobe_url: str = DEFAULT_EASYPANEL_LOBE_URL,
    canonical_lobe_url: str = DEFAULT_CANONICAL_LOBE_URL,
) -> list[ProbeResult]:
    """Execute the read-only probes in a deterministic order."""
    return [
        check_agent_health(agent_url),
        check_lobechat_proxy("lobechat_easypanel_proxy", easypanel_lobe_url, optional=False),
        check_dns_target(canonical_lobe_url),
        check_lobechat_proxy("lobechat_canonical_proxy", canonical_lobe_url, optional=True),
        check_cors(agent_url, easypanel_lobe_url.rstrip("/")),
        asyncio.run(check_websocket_challenge(agent_url, easypanel_lobe_url.rstrip("/"))),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe Cartório agent/LobeChat smoke test")
    parser.add_argument("--agent-url", default=DEFAULT_AGENT_URL)
    parser.add_argument("--easypanel-lobe-url", default=DEFAULT_EASYPANEL_LOBE_URL)
    parser.add_argument("--canonical-lobe-url", default=DEFAULT_CANONICAL_LOBE_URL)
    parser.add_argument("--strict-canonical", action="store_true", help="treat branded DNS/proxy warnings as failures")
    parser.add_argument("--json", action="store_true", help="print only redacted JSON results")
    args = parser.parse_args(argv)

    try:
        results = run_smoke(
            agent_url=args.agent_url,
            easypanel_lobe_url=args.easypanel_lobe_url,
            canonical_lobe_url=args.canonical_lobe_url,
        )
    except ValueError as exc:
        print(f"invalid setup: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False))
    else:
        print("Cartório agent safe smoke (no auth, no chat payload, no PII)")
        for result in results:
            marker = {"ok": "OK", "warn": "WARN", "error": "ERROR"}[result.status]
            print(f"[{marker}] {result.name}: {result.details}")

    failures = [result for result in results if result.status == "error"]
    if args.strict_canonical:
        failures.extend(result for result in results if result.status == "warn")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
