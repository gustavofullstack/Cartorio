"""Cron entrypoint para dead man's switch audit_log (A13).

Funcao `run_dead_mans_switch_check()` eh o ponto de entrada para o scheduler
externo (cron N8N / k8s CronJob / systemd timer). Faz:

1. Abre sessao DB (via `session_scope` do projeto)
2. Chama `check_audit_log_freshness(db, threshold_minutes)`
3. Se status != HEALTHY: loga alerta estruturado (placeholder Telegram GRUPO
   PIETRA SQUAD — integracao real fica para Sprint 5)
4. Retorna `AuditHealth` para inspecao / metricas

NAO rotaciona chaves, NAO mexe em audit/pii chain, NAO envia IM real
(escopo = observability + alerting, IM eh outra task).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.jobs.dead_mans_switch import (
    DEFAULT_THRESHOLD_MINUTES,
    AuditHealth,
    HealthStatus,
    check_audit_log_freshness,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CronRunResult:
    """Resultado de uma execucao do cron entrypoint.

    Attributes:
        health: AuditHealth retornado por check_audit_log_freshness.
        alerted: True se alerta foi enviado/logado (status != HEALTHY).
    """

    health: AuditHealth
    alerted: bool


def _send_telegram_placeholder(health: AuditHealth) -> None:
    """Placeholder Telegram GRUPO PIETRA SQUAD.

    TODO Sprint 5: integrar com TelegramBot (bot_id=settings.telegram_bot_id)
    + GRUPO PIETRA SQUAD (chat_id=settings.telegram_pietra_squad_chat_id).
    Por enquanto so loga localmente (NAO quebra se Telegram offline).
    """
    logger.error(
        "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER: %s | %s",
        health.status.value.upper(),
        health.alert,
    )


def run_dead_mans_switch_check(
    db: Session,
    threshold_minutes: int = DEFAULT_THRESHOLD_MINUTES,
    *,
    now=None,
) -> CronRunResult:
    """Entry point para cron externo — verifica freshness do audit_log.

    Args:
        db: SQLAlchemy session aberta pelo chamador (cron / endpoint admin).
        threshold_minutes: janela maxima em minutos. Default 60.
        now: override do "agora" para testes deterministicos.

    Returns:
        CronRunResult com `health` (AuditHealth) + `alerted` (bool).
    """
    health = check_audit_log_freshness(db, threshold_minutes, now=now)

    if health.status != HealthStatus.HEALTHY:
        _send_telegram_placeholder(health)
        return CronRunResult(health=health, alerted=True)

    return CronRunResult(health=health, alerted=False)


__all__ = [
    "CronRunResult",
    "run_dead_mans_switch_check",
]
