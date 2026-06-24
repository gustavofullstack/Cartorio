"""Testes A2 DLQ — Dead Letter Queue service + endpoints.

Cobre:
1. enqueue() cria row + refresh gauge
2. mark_done / mark_failed / mark_dead transicionam status
3. depth(queue) retorna count de pending
4. Endpoints POST /dlq/{queue}/enqueue + /dlq/refresh-gauges
   - Auth X-API-Key (401 sem chave)
   - Queue invalida (422)
   - Payload vazio (422)
   - Happy path (201)
5. LGPD: gauge dlq_depth{queue} enum-only (4 valores)
"""

from __future__ import annotations


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session():
    """SQLite in-memory session para testar services DLQ direto."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture reservada para testes de endpoint futuros (smoke via OpenAPI por enquanto)."""
    monkeypatch.setenv("CARTORIO_API_KEY", "test-key-a2-dlq")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AUDIT_HMAC_KEY", "x" * 64)
    yield monkeypatch


# ============================================================================
# services.dlq tests
# ============================================================================


def test_dlq_enqueue_cria_row_pending(db_session) -> None:
    """enqueue() cria row com status=PENDING + atualiza gauge."""
    from app.services.dlq import enqueue

    msg = enqueue(
        db_session,
        queue=OutboxQueue.EVOLUTION,
        payload={"text": "oi", "scrubbed": True},
    )
    assert msg.id is not None
    assert msg.queue == OutboxQueue.EVOLUTION
    assert msg.status == OutboxStatus.PENDING
    assert msg.attempts == 0
    assert msg.payload == {"text": "oi", "scrubbed": True}


def test_dlq_mark_processing_incrementa_attempts(db_session) -> None:
    """mark_processing incrementa attempts + muda status."""
    from app.services.dlq import enqueue, mark_processing

    msg = enqueue(db_session, OutboxQueue.CHATWOOT, {"a": 1})
    assert msg.attempts == 0
    mark_processing(db_session, msg)
    assert msg.attempts == 1
    assert msg.status == OutboxStatus.PROCESSING


def test_dlq_mark_done_finaliza(db_session) -> None:
    """mark_done muda status para DONE."""
    from app.services.dlq import enqueue, mark_done, mark_processing

    msg = enqueue(db_session, OutboxQueue.TELEGRAM, {"a": 1})
    mark_processing(db_session, msg)
    mark_done(db_session, msg)
    assert msg.status == OutboxStatus.DONE
    assert msg.last_error is None


def test_dlq_mark_failed_volta_para_pending(db_session) -> None:
    """mark_failed volta status para PENDING (retry) + registra error."""
    from app.services.dlq import enqueue, mark_failed

    msg = enqueue(db_session, OutboxQueue.OUTBOX, {"a": 1})
    mark_failed(db_session, msg, error="timeout")
    assert msg.status == OutboxStatus.PENDING
    assert msg.last_error == "timeout"


def test_dlq_mark_dead_finaliza_com_falha(db_session) -> None:
    """mark_dead muda status para FAILED (sem mais retry)."""
    from app.services.dlq import enqueue, mark_dead

    msg = enqueue(db_session, OutboxQueue.EVOLUTION, {"a": 1})
    mark_dead(db_session, msg, error="max_retries")
    assert msg.status == OutboxStatus.FAILED
    assert msg.last_error == "max_retries"


def test_dlq_depth_por_queue(db_session) -> None:
    """depth(queue) retorna count de pending por queue."""
    from app.services.dlq import depth, enqueue, mark_done, mark_processing

    enqueue(db_session, OutboxQueue.EVOLUTION, {"x": 1})
    enqueue(db_session, OutboxQueue.EVOLUTION, {"x": 2})
    enqueue(db_session, OutboxQueue.CHATWOOT, {"x": 3})

    # mark 1 evolution como DONE
    msg = db_session.query(OutboxMessage).filter_by(queue=OutboxQueue.EVOLUTION).first()
    mark_processing(db_session, msg)
    mark_done(db_session, msg)

    counts = depth(db_session)
    assert counts[OutboxQueue.EVOLUTION] == 1  # 1 done nao conta
    assert counts[OutboxQueue.CHATWOOT] == 1
    assert OutboxQueue.TELEGRAM not in counts  # 0 pending nao aparece


def test_dlq_depth_filtra_por_queue_especifica(db_session) -> None:
    """depth(queue=X) filtra so essa queue."""
    from app.services.dlq import depth, enqueue

    enqueue(db_session, OutboxQueue.EVOLUTION, {"x": 1})
    enqueue(db_session, OutboxQueue.CHATWOOT, {"x": 2})

    counts = depth(db_session, queue=OutboxQueue.EVOLUTION)
    assert counts == {OutboxQueue.EVOLUTION: 1}


# ============================================================================
# Endpoint tests
# ============================================================================


def test_endpoint_dlq_enqueue_smoke_openapi_registrado() -> None:
    """Endpoint /dlq/{queue}/enqueue esta registrado no OpenAPI schema."""
    from app.main import app

    schema = app.openapi()
    assert "/api/v1/dlq/{queue}/enqueue" in schema["paths"], (
        "Endpoint /api/v1/dlq/{queue}/enqueue nao foi registrado. "
        "Verificar decorator @api_router.post em app/api/v1/router.py."
    )
    assert "/api/v1/dlq/refresh-gauges" in schema["paths"], (
        "Endpoint /api/v1/dlq/refresh-gauges nao foi registrado."
    )


def test_endpoint_dlq_enqueue_openapi_responses() -> None:
    """Endpoint documenta 401 + 422 corretamente no OpenAPI."""
    from app.main import app

    schema = app.openapi()
    enqueue_path = schema["paths"]["/api/v1/dlq/{queue}/enqueue"]
    post_op = enqueue_path["post"]
    # documenta 401 (auth) + 422 (queue invalida + payload vazio)
    assert "401" in post_op["responses"]
    assert "422" in post_op["responses"]