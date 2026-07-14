"""test_integrations_outbox_dispatch_endpoint.py — OutboxMessage lifecycle tests.

Cobre /api/v1/integrations/outbox/dispatch:
- Erros de validacao (400/422/404/401)
- Lifecycle: happy path, failure, idempotencia, retries
- Dispatch por queue (evolution|chatwoot|telegram|outbox)
- Suporte a payload wrapper de Supabase (record.*)
- Modo de teste para queue=outbox
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
# B0.3 2026-06-25: /integrations/* agora exige X-API-Key (gap transversal)
TEST_API_KEY = "a" * 64
os.environ["CARTORIO_API_KEY"] = TEST_API_KEY

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402


@pytest.fixture
def AUTH_HEADERS() -> dict[str, str]:
    """Default headers para /integrations/* (B0.3 2026-06-25 auth gate)."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """Cliente de teste com DB in-memory e engine mockado."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def _seed_outbox(test_session_factory, **overrides) -> uuid.UUID:
    """Insere OutboxMessage de teste (status default=pending) e retorna id."""
    from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus

    defaults = {
        "queue": OutboxQueue.OUTBOX,
        "payload": {"text": "hello", "number": "5511999999999"},
        "status": OutboxStatus.PENDING,
        "attempts": 0,
        "last_error": None,
        "next_retry_at": None,
    }
    defaults.update(overrides)
    msg = OutboxMessage(**defaults)
    with test_session_factory() as s:
        s.add(msg)
        s.commit()
        s.refresh(msg)
        return msg.id


def _patch_dispatcher(queue_name: str) -> AsyncMock:
    """Substitui o handler em _DISPATCHERS por AsyncMock. Retorna o mock.

    IMPORTANTE: NAO restaura automaticamente (varios tests compartilham o dict
    global). Use o fixture `restore_dispatchers` para garantir cleanup entre tests.
    """
    from app.api.v1 import integrations
    from app.models.outbox_message import OutboxQueue

    mock = AsyncMock(return_value=None)
    integrations._DISPATCHERS[OutboxQueue(queue_name)] = mock
    return mock


@pytest.fixture(autouse=True)
def restore_dispatchers():
    """Garante que _DISPATCHERS eh restaurado entre tests."""
    from app.api.v1 import integrations

    saved = dict(integrations._DISPATCHERS)
    yield
    integrations._DISPATCHERS.clear()
    integrations._DISPATCHERS.update(saved)


# ============================================================================
# TestOutboxDispatchErrors — validacao de input e auth
# ============================================================================


class TestOutboxDispatchErrors:
    def test_400_on_bad_json(self, client, AUTH_HEADERS):
        """Body que nao eh JSON retorna 400 BAD_JSON."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
            content="{not valid json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["erro"] == "BAD_JSON"

    def test_422_missing_outbox_id(self, client, AUTH_HEADERS):
        """Sem outbox_id e sem record.id retorna 422 MISSING_FIELDS."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={"queue": "outbox", "payload": {}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["erro"] == "MISSING_FIELDS"

    def test_422_missing_queue(self, client, AUTH_HEADERS):
        """Sem queue e sem record.queue retorna 422 MISSING_FIELDS."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={"outbox_id": str(uuid.uuid4()), "payload": {}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["erro"] == "MISSING_FIELDS"

    def test_422_invalid_queue(self, client, AUTH_HEADERS):
        """Queue fora do enum retorna 422 INVALID_QUEUE."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "outbox_id": str(uuid.uuid4()),
                "queue": "rocket",
                "payload": {},
            },
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["erro"] == "INVALID_QUEUE"
        assert "evolution" in resp.json()["detail"]["valid"]

    def test_422_invalid_uuid_format(self, client, AUTH_HEADERS):
        """outbox_id em formato invalido retorna 422 INVALID_UUID."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={"outbox_id": "not-a-uuid", "queue": "outbox", "payload": {}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["erro"] == "INVALID_UUID"

    def test_404_when_outbox_not_in_db(self, client, AUTH_HEADERS):
        """UUID valido mas nao existente no DB retorna 404."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={"outbox_id": str(uuid.uuid4()), "queue": "outbox", "payload": {}},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["erro"] == "OUTBOX_NOT_FOUND"

    def test_401_without_api_key(self, client):
        """Sem X-API-Key retorna 401."""
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            json={
                "outbox_id": str(uuid.uuid4()),
                "queue": "outbox",
                "payload": {},
            },
        )
        assert resp.status_code == 401


# ============================================================================
# TestOutboxDispatchLifecycle — happy path, failures, idempotencia
# ============================================================================


class TestOutboxDispatchLifecycle:
    def test_happy_path_marks_done_evolution(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Success: status=done, attempts=1, last_error=None; dispatcher chamado."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(
            test_session_factory,
            status=OutboxStatus.PENDING,
        )
        mock_disp = _patch_dispatcher("evolution")
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "outbox_id": str(outbox_id),
                "queue": "evolution",
                "payload": {"number": "5511999999999", "text": "oi"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["attempts"] == 1
        assert data["error"] is None
        mock_disp.assert_awaited_once()

        from app.models.outbox_message import OutboxMessage

        with test_session_factory() as s:
            row = s.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
            assert row.status == OutboxStatus.DONE
            assert row.attempts == 1
            assert row.last_error is None

    def test_failure_marks_failed_increments_attempts_sets_next_retry(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Falha no dispatcher marca status=failed, attempts=1, next_retry_at ~+5min."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(test_session_factory, status=OutboxStatus.PENDING)
        before = datetime.now(timezone.utc)
        mock_disp = _patch_dispatcher("outbox")
        mock_disp.side_effect = RuntimeError("boom")
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "outbox_id": str(outbox_id),
                "queue": "outbox",
                "payload": {"text": "x"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["attempts"] == 1
        assert "RuntimeError" in data["error"]

        from app.models.outbox_message import OutboxMessage

        with test_session_factory() as s:
            row = s.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
            assert row.status == OutboxStatus.FAILED
            assert row.attempts == 1
            assert row.last_error is not None
            assert "RuntimeError" in row.last_error
            assert row.next_retry_at is not None
            # next_retry ~5min no futuro
            delta = (row.next_retry_at.replace(tzinfo=timezone.utc) - before).total_seconds()
            assert 290 <= delta <= 360  # 5min +/- margem

    def test_idempotent_when_already_done(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Status=done: retorna idempotent=True SEM chamar dispatcher."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(
            test_session_factory,
            status=OutboxStatus.DONE,
            attempts=2,
        )
        mock_disp = _patch_dispatcher("outbox")
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "outbox_id": str(outbox_id),
                "queue": "outbox",
                "payload": {"text": "x"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["idempotent"] is True
        assert data["attempts"] == 2  # NAO incrementou
        mock_disp.assert_not_called()

    def test_increments_attempts_on_each_call(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Cada call (mesmo com falha) incrementa attempts."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(
            test_session_factory, status=OutboxStatus.PENDING, attempts=0
        )

        mock_disp = _patch_dispatcher("outbox")
        mock_disp.side_effect = RuntimeError("fail")
        for _ in range(2):
            resp = client.post(
                "/api/v1/integrations/outbox/dispatch",
                headers=AUTH_HEADERS,
                json={
                    "outbox_id": str(outbox_id),
                    "queue": "outbox",
                    "payload": {"text": "x"},
                },
            )
            assert resp.status_code == 200

        from app.models.outbox_message import OutboxMessage

        with test_session_factory() as s:
            row = s.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
            assert row.attempts == 2

    def test_clears_last_error_on_success_after_failure(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Apos falha, sucesso limpa last_error."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(
            test_session_factory,
            status=OutboxStatus.FAILED,
            attempts=3,
            last_error="RuntimeError: previous",
        )

        _patch_dispatcher("outbox")
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "outbox_id": str(outbox_id),
                "queue": "outbox",
                "payload": {"text": "x"},
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["error"] is None

        from app.models.outbox_message import OutboxMessage

        with test_session_factory() as s:
            row = s.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
            assert row.last_error is None
            assert row.status == OutboxStatus.DONE

    def test_each_queue_dispatches_to_correct_handler(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Cada queue mapeia para seu dispatcher em _DISPATCHERS."""
        from app.models.outbox_message import OutboxQueue, OutboxStatus

        targets = [
            ("evolution",),
            ("chatwoot",),
            ("telegram",),
            ("outbox",),
        ]
        for (queue_name,) in targets:
            outbox_id = _seed_outbox(
                test_session_factory,
                queue=OutboxQueue(queue_name),
                status=OutboxStatus.PENDING,
            )
            mock_disp = _patch_dispatcher(queue_name)
            resp = client.post(
                "/api/v1/integrations/outbox/dispatch",
                headers=AUTH_HEADERS,
                json={
                    "outbox_id": str(outbox_id),
                    "queue": queue_name,
                    "payload": {
                        "text": "x",
                        "number": "5511999999999",
                        "chat_id": "123",
                        "bot_token": "tkn",
                    },
                },
            )
            assert resp.status_code == 200, queue_name
            assert resp.json()["status"] == "done"
            mock_disp.assert_awaited_once()

    def test_supports_payload_in_record_wrapper(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """Supabase nested: outbox_id/queue/payload vem de record.*."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(test_session_factory, status=OutboxStatus.PENDING)
        mock_disp = _patch_dispatcher("outbox")
        resp = client.post(
            "/api/v1/integrations/outbox/dispatch",
            headers=AUTH_HEADERS,
            json={
                "event": "INSERT",
                "table": "outbox_messages",
                "record": {
                    "id": str(outbox_id),
                    "queue": "outbox",
                    "payload": {"text": "from-record", "extra": 1},
                },
            },
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
        # Confirmou que recebeu payload do record (com extra)
        call_args = mock_disp.call_args
        payload = call_args[0][0]  # primeiro posicional
        assert payload["text"] == "from-record"
        assert payload["extra"] == 1


# ============================================================================
# TestOutboxDispatchTestMode — queue=outbox apenas loga
# ============================================================================


class TestOutboxDispatchTestMode:
    def test_outbox_queue_just_logs(
        self, client, test_session_factory, AUTH_HEADERS
    ):
        """queue=outbox apenas loga (modo de teste) sem chamar rede."""
        from app.models.outbox_message import OutboxStatus

        outbox_id = _seed_outbox(test_session_factory, status=OutboxStatus.PENDING)

        # Anexa handler explicitamente ao logger integrations.outbox
        # (caplog propagation pode falhar com _JsonFormatter).
        outbox_logger = logging.getLogger("integrations.outbox")
        records: list = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Capture(level=logging.INFO)
        outbox_logger.addHandler(handler)
        prev_level = outbox_logger.level
        outbox_logger.setLevel(logging.INFO)
        try:
            resp = client.post(
                "/api/v1/integrations/outbox/dispatch",
                headers=AUTH_HEADERS,
                json={
                    "outbox_id": str(outbox_id),
                    "queue": "outbox",
                    "payload": {"text": "test-mode-payload"},
                },
            )
        finally:
            outbox_logger.removeHandler(handler)
            outbox_logger.setLevel(prev_level)

        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
        # Logou info de "outbox (test mode)"
        assert any("outbox (test mode)" in r.getMessage() for r in records)
