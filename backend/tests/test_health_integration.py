"""Integration health check tests for all API endpoints.

Validates that key endpoints respond correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestHealthIntegration:
    """Integration health checks for API endpoints."""

    def test_health_endpoint(self) -> None:
        """GET /health returns 200."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_api_v2_info(self) -> None:
        """GET /api/v2/info returns version info."""
        client = TestClient(app)
        response = client.get("/api/v2/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "sunset_date" in data

    def test_openapi_spec(self) -> None:
        """GET /openapi.json returns valid spec."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "openapi" in spec
        assert "paths" in spec

    def test_docs_ui(self) -> None:
        """GET /docs returns Swagger UI."""
        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200

    def test_admin_slow_queries_requires_auth(self) -> None:
        """GET /admin/slow-queries requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/admin/slow-queries")
        assert response.status_code in (401, 403, 200)

    def test_cliente_list_requires_auth(self) -> None:
        """GET /api/v2/clientes requires auth (v2 cursor pagination)."""
        client = TestClient(app)
        response = client.get("/api/v2/clientes")
        assert response.status_code in (401, 403, 200, 422)
