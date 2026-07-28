"""Regressoes para timestamps UTC-naive sem ``datetime.utcnow()``."""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.audit_log import AuditLog
from app.models.atendimento import Atendimento
from app.models.base import utc_now_naive
from app.models.cliente import Cliente
from app.models.webhook_event import WebhookEvent
from app.services import pietra_memoria
from app.services.audit import AuditService
from app.services.pietra_coleta import upsert_cliente_por_telefone


def _assert_utc_naive(value: datetime) -> None:
    assert value.tzinfo is None
    assert abs((datetime.now(UTC) - value.replace(tzinfo=UTC)).total_seconds()) < 5


def test_utc_now_naive_is_utc_and_does_not_emit_deprecation_warning() -> None:
    """O helper explicita UTC e protege contra a volta de ``utcnow``."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        value = utc_now_naive()

    _assert_utc_naive(value)


def test_model_timestamp_defaults_are_utc_naive_without_deprecation_warning(db_session) -> None:
    """Defaults das colunas legadas continuam UTC-naive sem API depreciada."""
    cliente = Cliente(cpf_hash="a" * 64, nome="Pessoa de Teste")
    audit = AuditLog(
        actor_id="test",
        action="test.utc_timestamp",
        resource="test:utc_timestamp",
        hash="b" * 64,
        hmac_signature="c" * 64,
    )
    atendimento = Atendimento(canal="imessage", external_id="test", tipo="duvida")
    webhook = WebhookEvent(source="test", event_id="utc-default", payload_hash="d" * 64)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        db_session.add_all([cliente, audit, atendimento, webhook])
        db_session.flush()

    for value in (
        cliente.created_at,
        cliente.updated_at,
        audit.timestamp,
        atendimento.iniciado_em,
        webhook.received_at,
    ):
        _assert_utc_naive(value)


def test_audit_service_round_trip_uses_one_utc_naive_timestamp(db_session) -> None:
    """A entrada persistida recompõe a cadeia a partir do proprio timestamp."""
    entry = AuditService.log(
        db_session,
        actor_id="test-utc",
        action="audit.timestamp_round_trip",
        resource="audit:timestamp_round_trip",
        payload={"source": "regression"},
    )
    db_session.commit()
    db_session.refresh(entry)

    _assert_utc_naive(entry.timestamp)
    expected_timestamp = entry.timestamp.isoformat(timespec="microseconds")
    assert entry.hash == AuditService._compute_hash(None, entry.payload, expected_timestamp)

    chain_ok, last_valid_position = AuditService.verify_chain(db_session)
    assert chain_ok is True
    assert last_valid_position == 1


def test_pietra_memory_timestamp_paths_do_not_emit_deprecation_warning(monkeypatch) -> None:
    """Persistencia Redis/Postgres usa o helper nos dois caminhos de escrita."""
    db = MagicMock()
    monkeypatch.setattr(pietra_memoria, "get_redis", lambda: None)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert pietra_memoria.salvar_mensagem(
            db,
            telefone_hash="a" * 64,
            session_id="sessao-teste",
            role="user",
            content="Olá",
        )
        assert pietra_memoria.salvar_session_state(
            db,
            telefone_hash="a" * 64,
            session_id="sessao-teste",
            state={"etapa": "inicio"},
        )

    inserted_now = db.execute.call_args_list[0].args[1]["now"]
    state_now = db.execute.call_args_list[1].args[1]["now"]
    _assert_utc_naive(inserted_now)
    _assert_utc_naive(state_now)


def test_pietra_coleta_consent_timestamp_does_not_emit_deprecation_warning(db_session) -> None:
    """Registro de consentimento LGPD preserva UTC-naive sem warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        result = upsert_cliente_por_telefone(
            db_session,
            telefone="5534999990000",
            nome="Pessoa de Teste",
            consentimento_lgpd=True,
            consentimento_canal="imessage",
        )
        db_session.commit()

    cliente = db_session.get(Cliente, result.cliente_id)
    assert cliente is not None
    assert cliente.consentimento_em is not None
    _assert_utc_naive(cliente.consentimento_em)
