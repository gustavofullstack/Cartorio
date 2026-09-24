#!/usr/bin/env python3
"""MCP tools inventory — offline, no live server required (G7.09.T3 / T4).

Scans:
  1. backend/mcp_server.py  — @mcp.tool(name=...) registration count + names
  2. scripts/coding_vps_mcp_orchestrator.py — TOOLS registry via safe import
     (or static parse of _register_* dict keys if import fails)

Does NOT print secrets. Does NOT open network/SSH.

Usage:
  python3 scripts/mcp_tools_inventory.py
  python3 scripts/mcp_tools_inventory.py --json
  python3 scripts/mcp_tools_inventory.py --min-cartorio 7 --min-coding-vps 62
  python3 scripts/mcp_tools_inventory.py --check-mount   # static main.py wiring

Exit codes:
  0 — inventory OK (counts meet --min-*)
  1 — count below minimum or mount wiring missing
  2 — source files missing / parse error

Modified by Gustavo Almeida — G7 Wave 26 (G7.09.T3/T4).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "backend" / "mcp_server.py"
MAIN_PY = ROOT / "backend" / "app" / "main.py"
ORCHESTRATOR = ROOT / "scripts" / "coding_vps_mcp_orchestrator.py"
CONFIG_PY = ROOT / "backend" / "app" / "config.py"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"

# @mcp.tool( name="foo" ) — allows whitespace/newlines between ( and name=
TOOL_NAME_RE = re.compile(
    r"@mcp\.tool\(\s*name\s*=\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
# Fallback: bare @mcp.tool without name= uses def name
BARE_TOOL_RE = re.compile(
    r"@mcp\.tool\s*(?:\([^)]*\))?\s*\n\s*(?:async\s+)?def\s+(\w+)", re.M
)


def inventory_cartorio_mcp() -> dict[str, Any]:
    """Static parse of FastMCP tools in backend/mcp_server.py."""
    if not MCP_SERVER.is_file():
        return {"error": f"missing {MCP_SERVER}", "tools": [], "count": 0}

    text = MCP_SERVER.read_text(encoding="utf-8", errors="replace")
    names = TOOL_NAME_RE.findall(text)
    if not names:
        # decorator without explicit name= — use function name
        names = BARE_TOOL_RE.findall(text)

    # de-dupe preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)

    has_mcp_app = "def mcp_app(" in text
    has_http_app = "http_app" in text
    has_standalone = 'if __name__ == "__main__"' in text

    return {
        "source": str(MCP_SERVER.relative_to(ROOT)),
        "tools": ordered,
        "count": len(ordered),
        "has_mcp_app_factory": has_mcp_app,
        "has_http_app": has_http_app,
        "has_standalone_entrypoint": has_standalone,
        "method": "static_regex_@mcp.tool",
    }


def inventory_mount_wiring() -> dict[str, Any]:
    """Static checks that main.py mounts /mcp when MCP_SERVER_ENABLED."""
    result: dict[str, Any] = {
        "main": str(MAIN_PY.relative_to(ROOT)) if MAIN_PY.is_file() else None,
        "checks": {},
        "ok": False,
    }
    if not MAIN_PY.is_file():
        result["error"] = "main.py missing"
        return result

    text = MAIN_PY.read_text(encoding="utf-8", errors="replace")
    checks = {
        "settings.mcp_server_enabled_gate": "mcp_server_enabled" in text,
        "import_mcp_app": "mcp_app" in text and "mcp_server" in text,
        "mount_path_/mcp": 'app.mount("/mcp"' in text or "app.mount('/mcp'" in text,
        "combined_lifespan": "combined_lifespan" in text or "lifespan_context" in text,
        "mcp_servers_discovery_route": '"/mcp-servers"' in text
        or "'/mcp-servers'" in text,
    }
    result["checks"] = checks
    result["ok"] = all(checks.values())

    # config + .env.example hints (no secrets)
    if CONFIG_PY.is_file():
        cfg = CONFIG_PY.read_text(encoding="utf-8", errors="replace")
        result["config_has_mcp_server_enabled"] = "mcp_server_enabled" in cfg
    if ENV_EXAMPLE.is_file():
        envx = ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace")
        result["env_example_has_MCP_SERVER_ENABLED"] = "MCP_SERVER_ENABLED" in envx

    return result


def _static_orchestrator_tools(text: str) -> list[str]:
    """Parse TOOLS keys from _register_* return dicts via AST (best-effort)."""
    names: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # fallback: "tool_name": {"func":
        return re.findall(r'^\s{4,8}"([a-z][a-z0-9_]*)"\s*:\s*\{', text, re.M)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("_register_"):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                for key in child.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        names.append(key.value)
    # de-dupe
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def inventory_coding_vps() -> dict[str, Any]:
    """Load coding-vps TOOLS registry offline (import preferred, AST fallback)."""
    if not ORCHESTRATOR.is_file():
        return {"error": f"missing {ORCHESTRATOR}", "tools": [], "count": 0}

    method = "import_TOOLS"
    tools_map: dict[str, Any] = {}
    categories: dict[str, int] = {}

    try:
        # Import as plain module without executing main()
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "coding_vps_mcp_orchestrator_inventory",
            ORCHESTRATOR,
        )
        if spec is None or spec.loader is None:
            raise ImportError("spec load failed")
        mod = importlib.util.module_from_spec(spec)
        # Avoid running CLI side effects: module only registers TOOLS at import
        spec.loader.exec_module(mod)
        tools_map = dict(getattr(mod, "TOOLS", {}) or {})
        for name, info in tools_map.items():
            cat = (info or {}).get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
    except Exception as exc:  # noqa: BLE001 — offline inventory must not crash
        method = f"static_ast_fallback ({type(exc).__name__})"
        text = ORCHESTRATOR.read_text(encoding="utf-8", errors="replace")
        ordered = _static_orchestrator_tools(text)
        tools_map = {n: {} for n in ordered}

    ordered_names = sorted(tools_map.keys())
    if not categories and tools_map:
        for name, info in tools_map.items():
            cat = (
                (info or {}).get("category", "unknown")
                if isinstance(info, dict)
                else "unknown"
            )
            categories[cat] = categories.get(cat, 0) + 1

    return {
        "source": str(ORCHESTRATOR.relative_to(ROOT)),
        "tools": ordered_names,
        "count": len(ordered_names),
        "categories": dict(sorted(categories.items())),
        "category_count": len(categories),
        "method": method,
        "skill": ".agents/skills/coding-vps-tools-100/SKILL.md",
        "smoke_script": "scripts/validate_coding_vps_tools_60.sh",
        "note": (
            "Historical marketing said 100 tools; post-Squad-10/5 catalog is ~62+. "
            "Use `list` CLI for live count. SSH tools need Tailscale."
        ),
    }


def build_inventory(
    *,
    min_cartorio: int,
    min_coding_vps: int,
    check_mount: bool,
) -> dict[str, Any]:
    cartorio = inventory_cartorio_mcp()
    coding = inventory_coding_vps()
    mount = inventory_mount_wiring() if check_mount else None

    cartorio_ok = cartorio.get("count", 0) >= min_cartorio and not cartorio.get("error")
    coding_ok = coding.get("count", 0) >= min_coding_vps and not coding.get("error")
    mount_ok = True if mount is None else bool(mount.get("ok"))

    ok = bool(cartorio_ok and coding_ok and mount_ok)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "cartorio_mcp": cartorio,
        "coding_vps": coding,
        "mount_wiring": mount,
        "gates": {
            "min_cartorio": min_cartorio,
            "min_coding_vps": min_coding_vps,
            "cartorio_ok": cartorio_ok,
            "coding_vps_ok": coding_ok,
            "mount_ok": mount_ok,
        },
        "verdict": "PASS" if ok else "FAIL",
        "how_to_live_smoke": {
            "cartorio_mount": [
                "export MCP_SERVER_ENABLED=true  # backend/.env or env",
                "make dev  # or: cd backend && uv run uvicorn app.main:app --reload --port 8000",
                "curl -sS http://localhost:8000/mcp-servers | head -c 400",
                "curl -sS -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' "
                "-H 'Accept: application/json, text/event-stream' "
                '-d \'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\' | head -c 800',
                "make -C backend mcp-server  # standalone :8100",
            ],
            "coding_vps_offline": [
                "python3 scripts/coding_vps_mcp_orchestrator.py list",
                "bash scripts/validate_coding_vps_tools_60.sh --quick",
            ],
            "coding_vps_live_ssh": [
                "bash scripts/validate_coding_vps_tools_60.sh",
                "# needs SSH_PRIVATE_KEY + Tailscale to SSH_TAILSCALE_HOST",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline MCP tools inventory (G7.09)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--min-cartorio",
        type=int,
        default=7,
        help="Minimum cartorio @mcp.tool count (default 7)",
    )
    parser.add_argument(
        "--min-coding-vps",
        type=int,
        default=62,
        help="Minimum coding-vps TOOLS count (default 62)",
    )
    parser.add_argument(
        "--check-mount",
        action="store_true",
        default=True,
        help="Verify main.py /mcp mount wiring (default on)",
    )
    parser.add_argument(
        "--no-check-mount",
        action="store_true",
        help="Skip main.py mount wiring check",
    )
    args = parser.parse_args()
    check_mount = not args.no_check_mount

    inv = build_inventory(
        min_cartorio=args.min_cartorio,
        min_coding_vps=args.min_coding_vps,
        check_mount=check_mount,
    )

    if args.json:
        print(json.dumps(inv, indent=2, ensure_ascii=False))
    else:
        c = inv["cartorio_mcp"]
        v = inv["coding_vps"]
        g = inv["gates"]
        print(f"MCP tools inventory — {inv['verdict']}")
        print(
            f"  cartorio-mcp: {c.get('count', 0)} tools "
            f"(min {g['min_cartorio']}) [{c.get('method')}]"
        )
        for name in c.get("tools") or []:
            print(f"    - {name}")
        if c.get("error"):
            print(f"    ERROR: {c['error']}")
        print(
            f"  coding-vps:   {v.get('count', 0)} tools "
            f"(min {g['min_coding_vps']}) in {v.get('category_count', 0)} categories "
            f"[{v.get('method')}]"
        )
        for cat, n in (v.get("categories") or {}).items():
            print(f"    [{cat}] {n}")
        if v.get("error"):
            print(f"    ERROR: {v['error']}")
        if inv.get("mount_wiring"):
            m = inv["mount_wiring"]
            print(f"  /mcp mount wiring: {'OK' if m.get('ok') else 'FAIL'}")
            for k, ok in (m.get("checks") or {}).items():
                print(f"    {'OK' if ok else 'MISS'}  {k}")
        print(
            f"  gates: cartorio={g['cartorio_ok']} coding_vps={g['coding_vps_ok']} mount={g['mount_ok']}"
        )

    if inv["verdict"] != "PASS":
        return 1
    if inv["cartorio_mcp"].get("error") or inv["coding_vps"].get("error"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
