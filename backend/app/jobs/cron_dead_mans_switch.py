"""Cron entrypoint para dead man's switch audit_log (A13).

Funcao `run_dead_mans_switch_check()` eh o ponto de entrada LEGADO para o
scheduler externo (cron N8N / k8n CronJob / systemd timer). Retorna o shape
4-niveis (healthy/stale/critical/empty) — NAO ALTERAR (test
`test_dead_mans_switch_jobs.py` depende).

Para o briefing A13 (`/root/cartorio-a13-dead-mans-switch.yaml`), use
`run_dead_mans_switch_check_3lvl()` que retorna o shape 3-niveis
(healthy/warning/critical) com metrica Prometheus + Telegram GRUPO PIETRA
SQUAD.

NAO rotaciona chaves, NAO mexe em audit/pii chain.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.jobs.dead_mans_switch import (
    DEFAULT_THRESHOLD_MINUTES,
    AuditHealth,
    AuditHealth3Lvl,
    HealthStatus,
    HealthStatus3Lvl,
    check_audit_log_freshness,
    check_audit_log_freshness_3lvl,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CronRunResult:
    """Resultado de uma execucao do cron entrypoint (LEGADO 4-level).

    Attributes:
        health: AuditHealth retornado por check_audit_log_freshness.
        alerted: True se alerta foi enviado/logado (status != HEALTHY).
    """

    health: AuditHealth
    alerted: bool


def _send_telegram_placeholder(health: AuditHealth) -> None:
    """Placeholder Telegram GRUPO PIETRA SQUAD (LEGADO).

    TODO Sprint 5: integrar com TelegramBot (bot_id=settings.telegram_bot_id)
    + GRUPO PIETRA SQUAD (chat_id=settings.audit_alert_telegram_chat_id).
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
    """Entry point LEGADO para cron externo — verifica freshness do audit_log.

    Args:
        db: SQLAlchemy session aberta pelo chamador (cron / endpoint admin).
        threshold_minutes: janela maxima em minutos. Default 60.
        now: override do "agora" para testes deterministicos.

    Returns:
        CronRunResult com `health` (AuditHealth 4-level) + `alerted` (bool).
    """
    health = check_audit_log_freshness(db, threshold_minutes, now=now)

    if health.status != HealthStatus.HEALTHY:
        _send_telegram_placeholder(health)
        return CronRunResult(health=health, alerted=True)

    return CronRunResult(health=health, alerted=False)


# ============================================================================
# 3-level (briefing A13 /root/cartorio-a13-dead-mans-switch.yaml)
# ============================================================================


@dataclass(frozen=True)
class CronRunResult3Lvl:
    """Resultado de uma execucao do cron 3-level.

    Attributes:
        health: AuditHealth3Lvl retornado por check_audit_log_freshness_3lvl.
        alerted: True se alerta foi enviado/logado (status != HEALTHY).
        telegram_sent: True se Telegram foi enviado de fato (chat_id set).
    """

    health: AuditHealth3Lvl
    alerted: bool
    telegram_sent: bool


def _format_telegram_message_3lvl(health: AuditHealth3Lvl) -> str:
    """Formata mensagem Telegram GRUPO PIETRA SQUAD.

    Format canonico (briefing A13):
    [DEAD MAN'S SWITCH] audit_log {status}
    Ultima entry: {last_audit_ts ISO}
    Stale: {stale_seconds}s
    Threshold: {threshold_minutes}min
    Acao: verificar API + pipeline audit.
    """
    last = health.last_audit_ts.isoformat() if health.last_audit_ts else "(vazio)"
    stale = f"{health.stale_seconds}s" if health.stale_seconds is not None else "(vazio)"
    return (
        f"[DEAD MAN'S SWITCH] audit_log {health.status.value.upper()}\n"
        f"Ultima entry: {last}\n"
        f"Stale: {stale}\n"
        f"Threshold: {health.threshold_minutes}min\n"
        f"Acao: verificar API + pipeline audit."
    )


def _send_telegram_3lvl(message: str, chat_id: str | None) -> bool:
    """Placeholder Telegram GRUPO PIETRA SQUAD.

    TODO Sprint 5: integrar com TelegramBot (bot_id=settings.telegram_bot_id)
    + GRUPO PIETRA SQUAD (chat_id=settings.audit_alert_telegram_chat_id).
    Por enquanto so loga localmente (NAO quebra se Telegram offline).

    Returns:
        True se Telegram foi enviado (chat_id set + IM real), False se so logou.
    """
    if chat_id:
        # Placeholder: loga com chat_id. Sprint 5 faz HTTP POST de verdade.
        logger.error(
            "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER: chat_id=%s | %s",
            chat_id,
            message,
        )
        return True
    logger.error(
        "DEAD_MANS_SWITCH_TELEGRAM_PLACEHOLDER: (no chat_id configured) | %s",
        message,
    )
    return False


def run_dead_mans_switch_check_3lvl(
    db: Session,
    threshold_minutes: int | None = None,
    *,
    now=None,
) -> CronRunResult3Lvl:
    """Entry point 3-level (briefing A13) — verifica freshness + Telegram.

    Args:
        db: SQLAlchemy session aberta pelo chamador (cron / endpoint admin).
        threshold_minutes: janela maxima em minutos. Se None, usa
            `settings.audit_dead_mans_switch_minutes` (env
            `AUDIT_DEAD_MANS_SWITCH_MINUTES`, default 60).
        now: override do "agora" para testes deterministicos.

    Returns:
        CronRunResult3Lvl com `health` (AuditHealth3Lvl) + `alerted` (bool)
        + `telegram_sent` (bool).
    """
    # Lazy import de settings para evitar ciclo de import (config -> ?)
    from app.config import settings

    if threshold_minutes is None:
        threshold_minutes = settings.audit_dead_mans_switch_minutes

    health = check_audit_log_freshness_3lvl(db, threshold_minutes, now=now)

    if health.status == HealthStatus3Lvl.HEALTHY:
        return CronRunResult3Lvl(health=health, alerted=False, telegram_sent=False)

    message = _format_telegram_message_3lvl(health)
    chat_id = settings.audit_alert_telegram_chat_id
    sent = _send_telegram_3lvl(message, chat_id)

    return CronRunResult3Lvl(health=health, alerted=True, telegram_sent=sent)


__all__ = [
    "CronRunResult",
    "CronRunResult3Lvl",
    "run_dead_mans_switch_check",
    "run_dead_mans_switch_check_3lvl",
]
