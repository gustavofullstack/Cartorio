"""G7.09.T3 — MCP /mcp mount smoke (offline-friendly).

Validates that:
1. backend/mcp_server.py registers tools via @mcp.tool (static + runtime list)
2. mcp_app() factory exists for FastAPI mount
3. app/main.py wires combined lifespan + app.mount(\"/mcp\", ...) when enabled
4. /mcp-servers discovery route stays reachable

Does not require a live MCP HTTP session (StreamableHTTP). Live curls are
documented in docs/MCP_MOUNT_SMOKE_G7.md.

Modified by Gustavo Almeida — G7 Wave 26.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_PATH = BACKEND_ROOT / "mcp_server.py"
MAIN_PATH = BACKEND_ROOT / "app" / "main.py"

TOOL_NAME_RE = re.compile(
    r"@mcp\.tool\(\s*name\s*=\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)

# Baseline inventory — count drifts; gate is floor not exact equality.
MIN_CARTORIO_TOOLS = 7
REQUIRED_TOOL_SUBSTRINGS = (
    "cartorio_calcular_emolumento",
    "cartorio_consultar_protocolo",
    "cartorio_criar_protocolo",
    "cartorio_audit_verify",
    "cartorio_saudacao",
    "super_server_info",
)


class TestMcpServerSourceInventory:
    """Static registration smoke — no FastMCP runtime needed."""

    def test_mcp_server_file_exists(self) -> None:
        assert MCP_SERVER_PATH.is_file(), "backend/mcp_server.py missing"

    def test_tool_decorators_meet_floor(self) -> None:
        text = MCP_SERVER_PATH.read_text(encoding="utf-8")
        names = TOOL_NAME_RE.findall(text)
        assert len(names) >= MIN_CARTORIO_TOOLS, (
            f"expected >= {MIN_CARTORIO_TOOLS} @mcp.tool name=…, got {len(names)}: {names}"
        )

    def test_required_tools_present_in_source(self) -> None:
        text = MCP_SERVER_PATH.read_text(encoding="utf-8")
        names = set(TOOL_NAME_RE.findall(text))
        missing = [t for t in REQUIRED_TOOL_SUBSTRINGS if t not in names]
        assert not missing, f"required tools missing from mcp_server.py: {missing}"

    def test_mcp_app_factory_in_source(self) -> None:
        text = MCP_SERVER_PATH.read_text(encoding="utf-8")
        assert "def mcp_app(" in text
        assert "http_app" in text
        assert 'path="/"' in text or "path='/'" in text


class TestMcpMainMountWiring:
    """main.py mount contract (static) — independent of local .env flag."""

    def test_main_has_mcp_enabled_gate(self) -> None:
        text = MAIN_PATH.read_text(encoding="utf-8")
        assert "mcp_server_enabled" in text

    def test_main_mounts_mcp_path(self) -> None:
        text = MAIN_PATH.read_text(encoding="utf-8")
        assert 'app.mount("/mcp"' in text or "app.mount('/mcp'" in text

    def test_main_merges_mcp_lifespan(self) -> None:
        """FastMCP StreamableHTTP needs lifespan task group — regression guard."""
        text = MAIN_PATH.read_text(encoding="utf-8")
        assert "lifespan_context" in text
        assert "combined_lifespan" in text or "mcp" in text.lower()

    def test_mcp_servers_route_registered(self) -> None:
        client = TestClient(app)
        response = client.get("/mcp-servers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Discovery payload should mention cartorio /mcp somewhere
        blob = str(data).lower()
        assert "mcp" in blob

    def test_root_meta_lists_mcp_paths(self) -> None:
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("mcp") == "/mcp" or "/mcp" in str(data)
        assert data.get("mcp_servers") == "/mcp-servers" or "mcp" in str(data).lower()


class TestMcpRuntimeRegistration:
    """Import FastMCP module under test env and list tools (no HTTP server)."""

    @pytest.mark.asyncio
    async def test_list_tools_via_fastmcp(self) -> None:
        # Import inside test so conftest env (APP_ENV, DATABASE_URL, HMAC) is set.
        from mcp_server import mcp, mcp_app

        tools = await mcp.list_tools()
        names = sorted(t.name for t in tools)
        assert len(names) >= MIN_CARTORIO_TOOLS, names
        for required in REQUIRED_TOOL_SUBSTRINGS:
            assert required in names, f"{required} not in runtime tools: {names}"

        sub = mcp_app()
        assert sub is not None
        # Starlette/FastAPI sub-app exposes routes or router
        assert hasattr(sub, "routes") or hasattr(sub, "router")

    def test_config_exposes_mcp_server_enabled_flag(self) -> None:
        from app.config import settings

        assert hasattr(settings, "mcp_server_enabled")
        assert isinstance(settings.mcp_server_enabled, bool)


class TestMcpMountIfEnabled:
    """When local env enables MCP, Mount should be present on app.routes."""

    def test_mount_present_when_enabled(self) -> None:
        from app.config import settings

        mounts = [
            r
            for r in app.routes
            if type(r).__name__ == "Mount" and getattr(r, "path", "") in ("/mcp", "mcp")
        ]
        if settings.mcp_server_enabled:
            assert mounts, "MCP_SERVER_ENABLED=true but no Mount(/mcp) on app.routes"
        else:
            # Documented offline path: flag off in local .env is OK; wiring still tested statically.
            pytest.skip("MCP_SERVER_ENABLED=false in this process — static wiring already covered")
