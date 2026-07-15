"""Testes do endpoint /integrations/agent/health."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    """Client com engine patchado."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager
    from app.models.base import Base
    import app.models  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.atendimento  # noqa: F401
    import app.models.cliente  # noqa: F401
    import app.models.conversa  # noqa: F401
    import app.models.documento  # noqa: F401
    import app.models.protocolo  # noqa: F401
    import app.models.webhook_event  # noqa: F401

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    import app.db
    import app.main as app_main_module

    original_engine = app.db.engine
    original_session_scope = app.db.session_scope
    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    @contextmanager
    def test_session_scope():
        s = TestSessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.db.SessionLocal = TestSessionLocal
    app.db.session_scope = test_session_scope

    the_app = app_main_module.app
    try:
        with TestClient(the_app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


def test_agent_health_quando_tudo_ok(client) -> None:
    """OpenClaw alive + LLM reachable -> status=ok, 200."""
    responses = [_mock_response(200, {"x-openclaw-version": "1.2.3"}), _mock_response(200)]
    with patch("app.api.v1.integrations.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.get = AsyncMock(side_effect=responses)
        MockClient.return_value = instance

        resp = client.get("/api/v1/integrations/agent/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["openclaw"]["alive"] is True
    assert body["openclaw"]["version"] == "1.2.3"
    assert body["llm_provider"]["reachable"] is True
    assert "timestamp" in body


def test_agent_health_quando_openclaw_down(client) -> None:
    """OpenClaw down + LLM ok -> status=degraded."""
    from httpx import RequestError

    with patch("app.api.v1.integrations.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        # 1a chamada: OpenClaw fail. 2a chamada: LLM ok
        instance.get = AsyncMock(
            side_effect=[RequestError("connection refused"), _mock_response(200)]
        )
        MockClient.return_value = instance

        resp = client.get("/api/v1/integrations/agent/health")

    body = resp.json()
    assert body["status"] == "degraded"
    assert body["openclaw"]["alive"] is False
    assert body["openclaw"]["error"] is not None
    assert body["llm_provider"]["reachable"] is True


def test_agent_health_quando_tudo_down(client) -> None:
    """OpenClaw down + LLM down -> status=down."""
    from httpx import RequestError

    with patch("app.api.v1.integrations.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.get = AsyncMock(side_effect=RequestError("connection refused"))
        MockClient.return_value = instance

        resp = client.get("/api/v1/integrations/agent/health")

    body = resp.json()
    assert body["status"] == "down"


def test_agent_health_response_shape(client) -> None:
    """Response tem todos os campos esperados."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=_mock_response(200))

    with patch("app.api.v1.integrations.httpx.AsyncClient", return_value=mock):
        with patch("app.api.v1.integrations.httpx.AsyncClient", return_value=mock):
            resp = client.get("/api/v1/integrations/agent/health")

    body = resp.json()
    assert set(body.keys()) == {"status", "openclaw", "llm_provider", "timestamp"}
    assert set(body["openclaw"].keys()) == {"alive", "latency_ms", "version", "error"}
    assert set(body["llm_provider"].keys()) == {"provider", "model", "reachable", "error"}


def test_agent_health_nao_vaza_api_key(client) -> None:
    """Response NAO deve conter api_key em lugar nenhum."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=_mock_response(200))

    with patch("app.api.v1.integrations.httpx.AsyncClient", return_value=mock):
        with patch("app.api.v1.integrations.httpx.AsyncClient", return_value=mock):
            resp = client.get("/api/v1/integrations/agent/health")

    body_str = str(resp.json())
    # api_key nao pode aparecer em lugar nenhum
    from app.config import settings

    if settings.opencode_go_api_key:
        assert settings.opencode_go_api_key not in body_str
    if settings.openclaw_api_key:
        assert settings.openclaw_api_key not in body_str


def _mock_response(status_code: int, headers: dict | None = None) -> AsyncMock:
    """Helper que cria mock de httpx.Response."""
    m = AsyncMock()
    m.status_code = status_code
    m.headers = headers or {}
    return m
