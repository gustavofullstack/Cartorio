"""Testes unitarios para `app.services.audit_helper`.

Foco: log_mutation() e log_action_safe() — wrappers DRY de AuditService.log.
Cobertura alvo: 95%+ (gate 90%, ideal 95%).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.audit_helper import log_action_safe, log_mutation


def _fake_entry(audit_id: int = 99) -> MagicMock:
    """Mock minimal AuditLog-like entry retornado por AuditService.log."""
    entry = MagicMock()
    entry.id = audit_id
    return entry


def test_log_mutation_basic_returns_audit_id() -> None:
    db = MagicMock()
    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(123)
        result = log_mutation(
            db,
            actor_id="42",
            action="lgpd.direito_esquecimento",
            resource="cliente:42",
            payload={"motivo": "consent_revoked"},
        )
    assert result == 123
    mock_log.assert_called_once()
    kwargs = mock_log.call_args.kwargs
    assert kwargs["actor_id"] == "42"
    assert kwargs["action"] == "lgpd.direito_esquecimento"
    assert kwargs["resource"] == "cliente:42"
    assert kwargs["actor_type"] == "user"
    assert kwargs["payload"] == {"motivo": "consent_revoked"}


def test_log_mutation_with_actor_type_system() -> None:
    db = MagicMock()
    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(7)
        result = log_mutation(
            db,
            actor_id="cron",
            actor_type="system",
            action="retencao.exec",
            resource="cliente:*",
            payload={},
        )
    assert result == 7
    kwargs = mock_log.call_args.kwargs
    assert kwargs["actor_type"] == "system"


def test_log_mutation_defensive_returns_zero_on_exception() -> None:
    db = MagicMock()
    with patch(
        "app.services.audit_helper.AuditService.log",
        side_effect=RuntimeError("db down"),
    ):
        result = log_mutation(
            db,
            actor_id="1",
            action="test.fail",
            resource="t:1",
            payload={},
        )
    assert result == 0  # best-effort


def test_log_mutation_request_extracts_context() -> None:
    """Quando request FastAPI e passada, contexto e extraido via audit_kwargs."""
    db = MagicMock()
    fake_request = MagicMock()
    fake_state = MagicMock()
    fake_state.request_id = "req-abc-123"
    fake_state.client_ip = "10.1.2.3"
    fake_state.user_agent = "test-ua/1.0"
    fake_state.canal = "telegram"
    fake_request.state = fake_state

    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(11)
        log_mutation(
            db,
            actor_id="bot",
            actor_type="bot",
            action="conversa.received",
            resource="telegram:user:1",
            payload={"text": "oi"},
            request=fake_request,
        )
    kwargs = mock_log.call_args.kwargs
    assert kwargs["request_id"] == "req-abc-123"
    assert kwargs["ip"] == "10.1.2.3"
    assert kwargs["user_agent"] == "test-ua/1.0"
    assert kwargs["canal"] == "telegram"


def test_log_mutation_request_partial_override() -> None:
    """Overrides explicitos tem prioridade sobre request extraction."""
    db = MagicMock()
    fake_request = MagicMock()
    fake_state = MagicMock()
    fake_state.request_id = "req-1"
    fake_state.client_ip = "10.1.1.1"
    fake_state.user_agent = "auto-ua"
    fake_state.canal = "auto-canal"
    fake_request.state = fake_state

    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(1)
        log_mutation(
            db,
            actor_id="bot",
            action="x",
            resource="y",
            payload={},
            request=fake_request,
            canal="whatsapp",  # override
            ip="127.0.0.1",
        )
    kwargs = mock_log.call_args.kwargs
    assert kwargs["canal"] == "whatsapp"
    assert kwargs["ip"] == "127.0.0.1"
    assert kwargs["user_agent"] == "auto-ua"  # nao foi overridden


def test_log_mutation_no_request_keeps_overrides() -> None:
    db = MagicMock()
    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(1)
        log_mutation(
            db,
            actor_id="system",
            action="cron.tick",
            resource="system",
            payload={"k": "v"},
            canal="system",
            ip=None,
            user_agent=None,
            request=None,
        )
    kwargs = mock_log.call_args.kwargs
    assert kwargs["request_id"] is None
    assert kwargs["canal"] == "system"


def test_log_action_safe_defaults_actor_type_system() -> None:
    db = MagicMock()
    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(5)
        result = log_action_safe(
            db,
            actor_id="dlq-task-99",
            action="dlq.retry",
            resource="outbox:42",
            payload={"attempt": 3},
        )
    assert result == 5
    kwargs = mock_log.call_args.kwargs
    assert kwargs["actor_type"] == "system"
    assert kwargs["actor_id"] == "dlq-task-99"
    # Garantir que request=None foi passado internamente
    assert kwargs.get("request_id") is None


def test_log_action_safe_defensive_zero_on_exception() -> None:
    db = MagicMock()
    with patch(
        "app.services.audit_helper.AuditService.log",
        side_effect=ValueError("bad payload"),
    ):
        result = log_action_safe(
            db,
            actor_id="task-1",
            action="x",
            resource="y",
            payload={},
        )
    assert result == 0


def test_log_mutation_payload_not_mutated() -> None:
    """DRY wrapper NAO modifica payload do caller."""
    db = MagicMock()
    original_payload = {"chave": "valor", "lista": [1, 2, 3]}
    with patch("app.services.audit_helper.AuditService.log") as mock_log:
        mock_log.return_value = _fake_entry(1)
        log_mutation(
            db,
            actor_id="1",
            action="x",
            resource="y",
            payload=original_payload,
        )
    # Garantir que o caller ainda tem o payload original
    assert original_payload == {"chave": "valor", "lista": [1, 2, 3]}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
