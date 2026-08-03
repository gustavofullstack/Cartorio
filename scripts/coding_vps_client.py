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
        url = "XXBASEURLXX/call/XXTOOLXX"
        url = url.replace("XXBASEURLXX", self.base_url).replace("XXTOOLXX", tool_name)
        return self._post(url, kwargs)

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "body": e.read().decode()[:500]}
        except Exception as e:
            return {"error": str(e)}

    def _post(self, url: str, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=body, method="POST", headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "body": e.read().decode()[:500]}
        except Exception as e:
            return {"error": str(e)}

    def __repr__(self) -> str:
        return f"CodingVPSClient({self.base_url})"


class CodingVPSMCPClient:
    """MCP stdio client for coding-vps MCP orchestrator."""

    def __init__(self, script_path: str = None):
        self.script_path = (
            script_path
            or "/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py"
        )
        self.proc = None

    def start(self):
        """Start MCP stdio subprocess."""
        self.proc = subprocess.Popen(
            ["python3", self.script_path, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def call(self, tool_name: str, **kwargs) -> dict:
        """Call a tool via MCP stdio (JSON-RPC 2.0)."""
        if not self.proc:
            self.start()
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": kwargs},
            "id": 1,
        }
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        response_line = self.proc.stdout.readline()
        return json.loads(response_line) if response_line else {"error": "no response"}

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
            self.proc = None


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python coding_vps_client.py list")
        print("  python coding_vps_client.py call <tool> [k=v ...]")
        sys.exit(1)

    client = CodingVPSClient()
    cmd = sys.argv[1]
    if cmd == "list":
        tools = client.list_tools()
        print(f"Available tools: {len(tools)}")
        for name, info in tools.items():
            print(f"  [{info['category']:12}] {name}({', '.join(info['args'])})")
    elif cmd == "call":
        tool_name = sys.argv[2]
        kwargs = {}
        for arg in sys.argv[3:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kwargs[k] = v
        result = client.call(tool_name, **kwargs)
        print(json.dumps(result, indent=2, default=str))
