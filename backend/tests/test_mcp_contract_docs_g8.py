"""Regression checks for the public MCP endpoint and tools descriptor.

The mounted FastMCP sub-app uses an internal ``/`` path.  Its public path is
therefore exactly ``/mcp``; documenting ``/mcp/mcp`` makes clients fail before
the JSON-RPC handshake.  The descriptor is a checked-in client aid and must
remain a complete inventory of the source registrations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
MCP_SERVER = BACKEND_ROOT / "mcp_server.py"
TOOLS_DESCRIPTION = BACKEND_ROOT / "tools_description.json"
CLIENT_CONFIG = REPO_ROOT / "scripts" / "mcp_config.cartorio-api.example.json"

TOOL_NAME_RE = re.compile(r'@mcp\.tool\(\s*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def test_mcp_public_endpoint_is_not_duplicated() -> None:
    """The mount prefix plus internal root resolves to one public /mcp path."""
    descriptor = json.loads(TOOLS_DESCRIPTION.read_text(encoding="utf-8"))
    client_config = json.loads(CLIENT_CONFIG.read_text(encoding="utf-8"))

    assert descriptor["server"]["url"].endswith("/mcp")
    assert descriptor["configuracao_cliente"]["url"].endswith("/mcp")
    assert "/mcp/mcp" not in json.dumps(descriptor)
    assert client_config["mcpServers"]["cartorio-api"]["url"].endswith("/mcp")
    assert client_config["mcpServers"]["cartorio-api-local"]["env"]["MCP_SERVER_PORT"] == "8100"


def test_tools_descriptor_matches_source_inventory() -> None:
    """Every registered tool is discoverable in the checked-in descriptor."""
    source_tools = TOOL_NAME_RE.findall(MCP_SERVER.read_text(encoding="utf-8"))
    descriptor = json.loads(TOOLS_DESCRIPTION.read_text(encoding="utf-8"))
    documented_tools = [tool["name"] for tool in descriptor["tools"]]

    assert len(source_tools) == len(set(source_tools))
    assert len(documented_tools) == len(set(documented_tools))
    assert set(documented_tools) == set(source_tools)
    assert descriptor["version"] == "0.6.0"
    assert descriptor["server"]["version"] == "0.6.0"


def test_tools_descriptor_is_served_from_api() -> None:
    """Clients can retrieve the checked-in descriptor at the documented URL."""
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/tools_description.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["server"]["url"].endswith("/mcp")
