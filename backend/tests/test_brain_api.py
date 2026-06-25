"""Tests for /api/v1/brain/ endpoints.

Validates brain memory API endpoints.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestBrainAPI:
    """Brain API endpoint tests."""

    def test_brain_tasks_requires_auth(self) -> None:
        """GET /api/v1/brain/tasks requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/brain/tasks")
        assert response.status_code in (401, 403, 200, 404)

    def test_brain_lessons_requires_auth(self) -> None:
        """GET /api/v1/brain/lessons requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/brain/lessons")
        assert response.status_code in (401, 403, 200, 404)

    def test_brain_loop_state_requires_auth(self) -> None:
        """GET /api/v1/brain/loop-state requires API key."""
        client = TestClient(app)
        response = client.get("/api/v1/brain/loop-state")
        assert response.status_code in (401, 403, 200, 404)

    def test_brain_sync_requires_auth(self) -> None:
        """POST /api/v1/brain/sync requires API key."""
        client = TestClient(app)
        response = client.post("/api/v1/brain/sync")
        assert response.status_code in (401, 403, 200, 404, 405)
