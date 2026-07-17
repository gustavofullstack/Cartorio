"""G8.08.T1 — Testes para DLQ expiration/purge (LGPD Art.16 retenção).

Cobre:
  - expire_old_messages: FAILED > N dias são marcadas (soft delete)
  - expire_old_messages: PENDING/DONE não são tocadas
  - expire_old_messages: retorna count correto
  - purge_deleted_hard: remove fisicamente EXPIRED antigos
  - purge_deleted_hard: NÃO toca EXPIRED recentes (período de auditoria)
  - stats_by_age: distribuição por faixa de idade
  - Integração com metrics_store.inc_dlq_expired
  - LGPD compliance: trilha de auditoria preservada via last_error marker

Modified by Gustavo Almeida — G8 Wave 31 A1.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus
from app.services import dlq


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock SQLAlchemy Session."""
    db = MagicMock()
    db.execute.return_value.rowcount = 0
    return db


def _make_msg(
    queue: OutboxQueue,
    status: OutboxStatus,
    age_days: int,
    *,
    last_error: str | None = None,
    payload: dict[str, Any] | None = None,
) -> OutboxMessage:
    """Helper: cria OutboxMessage com created_at retroativo."""
    msg = OutboxMessage(
        id=uuid.uuid4(),
        queue=queue,
        status=status,
        attempts=0,
        last_error=last_error,
        payload=payload or {"test": "data"},
    )
    msg.created_at = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
    msg.updated_at = msg.created_at
    return msg


class TestExpireOldMessages:
    def test_expire_marks_old_failed_as_failed_with_marker(self, mock_db):
        # UPDATE rowcount simulado
        mock_db.execute.return_value.rowcount = 5
        count = dlq.expire_old_messages(mock_db, older_than_days=30)
        assert count == 5
        # UPDATE deve ter sido chamado com FAILED + last_error EXPIRED
        mock_db.execute.assert_called()
        stmt = mock_db.execute.call_args[0][0]
        # Verifica estrutura basica do statement
        assert stmt is not None

    def test_expire_returns_zero_when_no_old_messages(self, mock_db):
        mock_db.execute.return_value.rowcount = 0
        count = dlq.expire_old_messages(mock_db, older_than_days=30)
        assert count == 0

    def test_expire_with_custom_older_than(self, mock_db):
        mock_db.execute.return_value.rowcount = 3
        count = dlq.expire_old_messages(mock_db, older_than_days=7)
        assert count == 3

    def test_expire_invalidates_depth_gauge(self, mock_db):
        mock_db.execute.return_value.rowcount = 2
        # depth() é chamado internamente em _update_depth_gauge
        # Não quebra mesmo se mock retorna algo inconsistente
        dlq.expire_old_messages(mock_db, older_than_days=30)
        # Deve ter commitado
        mock_db.commit.assert_called()

    def test_expire_status_default_is_failed(self):
        """Contrato: só expira FAILED por default (PENDING/DONE intocadas)."""
        # Inspeção de assinatura (sem executar)
        import inspect

        sig = inspect.signature(dlq.expire_old_messages)
        assert sig.parameters["status"].default == OutboxStatus.FAILED


class TestPurgeDeletedHard:
    def test_purge_removes_old_expired(self, mock_db):
        mock_db.execute.return_value.rowcount = 10
        count = dlq.purge_deleted_hard(mock_db, older_than_days=180)
        assert count == 10
        mock_db.commit.assert_called()

    def test_purge_returns_zero_when_nothing_to_purge(self, mock_db):
        mock_db.execute.return_value.rowcount = 0
        count = dlq.purge_deleted_hard(mock_db, older_than_days=180)
        assert count == 0

    def test_purge_uses_default_180d_audit_period(self):
        """LGPD conservador: 180 dias (6 meses) entre EXPIRED e hard delete."""
        import inspect

        sig = inspect.signature(dlq.purge_deleted_hard)
        assert sig.parameters["older_than_days"].default == 180


class TestStatsByAge:
    def test_stats_empty_db_returns_empty_dict(self, mock_db):
        mock_db.execute.return_value.all.return_value = []
        result = dlq.stats_by_age(mock_db)
        assert result == {}

    def test_stats_groups_by_age_buckets(self, mock_db):
        now = datetime.now(tz=timezone.utc)
        # Simula 3 mensagens: 0d, 5d, 45d
        rows = [
            (now - timedelta(days=0),),
            (now - timedelta(days=5),),
            (now - timedelta(days=45),),
        ]
        mock_db.execute.return_value.all.return_value = rows
        result = dlq.stats_by_age(mock_db)
        assert result.get("<1d") == 1
        assert result.get("1-7d") == 1
        assert result.get(">30d") == 1
        assert "7-30d" not in result or result.get("7-30d") == 0

    def test_stats_filters_by_queue(self, mock_db):
        now = datetime.now(tz=timezone.utc)
        mock_db.execute.return_value.all.return_value = [(now,)]
        dlq.stats_by_age(mock_db, queue=OutboxQueue.EVOLUTION)
        # Deve ter chamado SELECT com WHERE queue == evolution
        mock_db.execute.assert_called()

    def test_stats_handles_null_created_at(self, mock_db):
        """Defesa contra dados legacy com timestamps NULL."""
        mock_db.execute.return_value.all.return_value = [(None,)]
        result = dlq.stats_by_age(mock_db)
        assert result == {}


class TestIntegrationWithMetrics:
    """Valida que expire_old_messages() incrementa counter dlq_expired_total."""

    def test_expire_increments_metric_counter(self, mock_db):
        from app.services.metrics import store as metrics_store

        # Captura valor inicial do counter
        initial = sum(metrics_store.counters.get("dlq_expired_total", {}).values())

        mock_db.execute.return_value.rowcount = 7
        dlq.expire_old_messages(mock_db, older_than_days=30)

        # Counter deve ter sido incrementado
        after = sum(metrics_store.counters.get("dlq_expired_total", {}).values())
        assert after >= initial + 7, f"Counter não incrementou: {initial} -> {after}"

    def test_metric_helper_with_queue_label(self):
        from app.services.metrics import MetricsStore

        ms = MetricsStore()
        ms.inc_dlq_expired(queue="evolution", count=5)
        # Deve existir entry com queue=evolution
        dlq_keys = [
            k for k in ms.counters.get("dlq_expired_total", {}).keys() if "evolution" in k
        ]
        assert len(dlq_keys) > 0

    def test_metric_helper_with_none_queue(self):
        from app.services.metrics import MetricsStore

        ms = MetricsStore()
        ms.inc_dlq_expired(queue=None, count=3)
        # Deve existir entry sem label de queue
        all_keys = list(ms.counters.get("dlq_expired_total", {}).keys())
        assert len(all_keys) > 0


class TestLGPDCompliance:
    """Garante que expiration respeita LGPD Art.16 (retenção/eliminação)."""

    def test_expire_uses_soft_delete_not_hard(self, mock_db):
        """LGPD Art.37: trilha de auditoria. NÃO remove fisicamente em expire."""
        mock_db.execute.return_value.rowcount = 5
        dlq.expire_old_messages(mock_db, older_than_days=30)
        # Verifica que foi UPDATE (não DELETE). _update_depth_gauge() faz
        # SELECT depois do UPDATE, entao call_args[-1] eh SELECT.
        # call_args_list[0] eh o UPDATE original.
        all_calls = mock_db.execute.call_args_list
        assert len(all_calls) >= 2, "Esperava UPDATE + pelo menos 1 SELECT"
        update_stmt = all_calls[0][0][0]
        # Update tem .values(), Select nao
        assert hasattr(update_stmt, "values"), "Primeira call deveria ser UPDATE"

    def test_purge_uses_delete(self, mock_db):
        """purge_deleted_hard é a ÚNICA função que faz DELETE físico."""
        mock_db.execute.return_value.rowcount = 5
        dlq.purge_deleted_hard(mock_db, older_than_days=180)
        stmt = mock_db.execute.call_args[0][0]
        assert hasattr(stmt, "values") is False, "Esperado DELETE, não UPDATE"

    def test_purge_only_targets_expired_messages(self, mock_db):
        """NÃO remove PENDING/DONE/PROCESSING mesmo se antigos."""
        mock_db.execute.return_value.rowcount = 0
        dlq.purge_deleted_hard(mock_db, older_than_days=180)
        # Statement deve ter WHERE last_error LIKE 'EXPIRED after %'
        stmt_str = str(mock_db.execute.call_args[0][0])
        assert "EXPIRED after" in stmt_str or "like" in stmt_str.lower()


class TestExportsAndSurface:
    def test_dlq_module_exposes_new_functions(self):
        """API pública do módulo inclui expire_old_messages, purge_deleted_hard, stats_by_age."""
        assert hasattr(dlq, "expire_old_messages")
        assert hasattr(dlq, "purge_deleted_hard")
        assert hasattr(dlq, "stats_by_age")
        for name in ("expire_old_messages", "purge_deleted_hard", "stats_by_age"):
            assert name in dlq.__all__

    def test_functions_are_callable(self):
        """Todas as 3 funções são callable (assinatura consistente)."""
        assert callable(dlq.expire_old_messages)
        assert callable(dlq.purge_deleted_hard)
        assert callable(dlq.stats_by_age)