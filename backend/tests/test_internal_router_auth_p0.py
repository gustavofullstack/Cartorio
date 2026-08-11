"""Regressoes de autenticacao para superficies internas com memoria e PII."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.brain import _snapshot_path
from app.config import get_settings
from app.main import app


@pytest.fixture
def enforce_internal_auth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INTERNAL_API_REQUIRE_KEY", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/brain/tasks"),
        ("post", "/api/v1/brain/lesson"),
        ("get", "/api/v1/pietra/memoria/5511998765432"),
        ("post", "/api/v1/pietra/chat/completions"),
        ("get", "/api/v1/agent-hermes/status"),
        ("post", "/api/v1/agent-hermes/execute"),
    ],
)
def test_internal_surfaces_reject_missing_api_key(
    method: str,
    path: str,
    enforce_internal_auth,
) -> None:
    response = getattr(TestClient(app), method)(path)
    assert response.status_code == 401


def test_brain_snapshot_traversal_is_stopped_by_auth_gate(enforce_internal_auth) -> None:
    response = TestClient(app).get("/api/v1/brain/context/restore/%2E%2E%2F.env")
    assert response.status_code in {401, 404}


def test_brain_snapshot_id_rejects_path_traversal_after_auth() -> None:
    with pytest.raises(HTTPException) as exc:
        _snapshot_path("../.env")
    assert exc.value.status_code == 422
