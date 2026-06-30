"""Testes A15 — endpoint GET /api/v1/admin/pool.

Cobre:
1. Auth: 401 sem X-API-Key
2. Auth: 401 com X-API-Key invalida
3. Happy path: 200 com stats do pool
4. Estrutura: chaves esperadas (backend, pool_size, checked_out, etc)
5. SQLite: retorna note 'SQLite nao usa pool de conexoes'
"""

from __future__ import annotations

import os

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64
os.environ.setdefault("JWT_SECRET", "z" * 32)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.api.v1.router import api_router  # noqa: E402

VALID_KEY = "a" * 64


@pytest.fixture
def client() -> TestClient:
    """TestClient com api_router (que ja contem /admin/pool registrado)."""
    test_app = FastAPI()
    test_app.include_router(api_router, prefix="/api/v1")
    return TestClient(test_app)


def test_pool_401_sem_x_api_key(client: TestClient) -> None:
    """Sem header X-API-Key retorna 401 (problem+json RFC 7807)."""
    resp = client.get("/api/v1/admin/pool")
    assert resp.status_code == 401
    body = resp.json()
    # Aceita problem+json (RFC 7807) ou formato com detail.erro
    assert "status" in body or "detail" in body or "erro" in body


def test_pool_401_com_key_invalida(client: TestClient) -> None:
    """X-API-Key errado retorna 401."""
    resp = client.get("/api/v1/admin/pool", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_pool_200_com_key_valida(client: TestClient) -> None:
    """X-API-Key correto retorna 200 com stats do pool."""
    resp = client.get("/api/v1/admin/pool", headers={"X-API-Key": VALID_KEY})
    assert resp.status_code == 200
    body = resp.json()
    assert "backend" in body
    assert "pool_size" in body
    assert "checked_out" in body
    assert "utilization_pct" in body
    assert isinstance(body["utilization_pct"], float)


def test_pool_sqlite_retorna_note(client: TestClient) -> None:
    """Em SQLite retorna nota explicativa (nao usa pool)."""
    resp = client.get("/api/v1/admin/pool", headers={"X-API-Key": VALID_KEY})
    body = resp.json()
    # Em test SQLite :memory: o backend eh 'sqlite'
    if body["backend"] == "sqlite":
        assert "note" in body
        assert "SQLite" in body["note"]
        assert body["pool_size"] == 0
