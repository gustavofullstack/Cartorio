"""Python client for coding-vps-orchestrator MCP server.

Usage:
    # HTTP mode (REST)
    from coding_vps_client import CodingVPSClient
    client = CodingVPSClient("http://100.99.172.84:8100")
    print(client.call("chat_minimax", prompt="hello", max_tokens=80))
    print(client.call("list_services"))

    # MCP stdio mode (subprocess)
    from coding_vps_client import CodingVPSMCPClient
    mcp = CodingVPSMCPClient()
    mcp.start()
    print(mcp.call("chat_minimax", prompt="hello"))
    mcp.stop()
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


class CodingVPSClient:
    """REST client for coding-vps MCP orchestrator HTTP server."""

    def __init__(self, base_url: str = "http://100.99.172.84:8100", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_tools(self) -> dict:
        """List all 85 tools available."""
        return self._get("/tools")

    def call(self, tool_name: str, **kwargs) -> dict:
        """Call a tool by name with kwargs."""
        url = f"{self.base_url}/call/{tool_name}"
        return self._post(url, kwargs)

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e