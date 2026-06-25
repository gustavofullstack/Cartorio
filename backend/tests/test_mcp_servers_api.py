"""Tests for /mcp-servers endpoint.

Validates MCP servers discovery endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestMCPServersAPI:
    """MCP servers endpoint tests."""

    def test_mcp_servers_returns_200(self) -> None:
        """GET /mcp-servers returns 200."""
        client = TestClient(app)
        response = client.get("/mcp-servers")
        assert response.status_code == 200

    def test_mcp_servers_no_auth_required(self) -> None:
        """GET /mcp-servers works without authentication."""
        client = TestClient(app)
        response = client.get("/mcp-servers")
        assert response.status_code not in (401, 403)

    def test_mcp_servers_returns_json(self) -> None:
        """GET /mcp-servers returns JSON response."""
        client = TestClient(app)
        response = client.get("/mcp-servers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))
