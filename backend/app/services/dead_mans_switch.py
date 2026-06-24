"""Dead man's switch — verifica se audit log esta vivo (A13).

Job: se ultima entrada audit_log > 1h, alerta via Telegram/Chatwoot.
LGPD: alerta nao expoe conteudo, apenas timestamp.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

DEAD_THRESHOLD = timedelta(hours=1)
COLD_START_THRESHOLD = timedelta(minutes=5)  # Janela para considerar cold start


def last_audit_timestamp(db: Session) -> datetime | None:
    """Retorna timestamp do ultimo audit log, ou None se tabela vazia."""
    stmt = select(func.max(AuditLog.timestamp))
    result = db.execute(stmt).scalar()
    return result


def check_audit_log_alive(db: Session) -> dict:
    """Verifica se audit log esta vivo (A13 dead man's switch).

    Returns:
        dict com chaves:
          - alive (bool): True se <= 1h, False caso contrario
          - cold_start (bool): True se tabela vazia e app comecou ha > 5min
          - last_seen (datetime|None): timestamp do ultimo audit
          - seconds_since_last (int|None): segundos desde ultimo audit (ou None)
    """
    last = last_audit_timestamp(db)
    now = datetime.now(tz=timezone.utc)
    if last is None:
        return {
            "alive": False,
            "cold_start": True,
            "last_seen": None,
            "seconds_since_last": None,
        }
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    delta = now - last
    return {
        "alive": delta <= DEAD_THRESHOLD,
        "cold_start": False,
        "last_seen": last,
        "seconds_since_last": int(delta.total_seconds()),
    }


def send_alert(message: str) -> None:
    """Envia alerta (Telegram/Chatwoot/log). Implementacao minimal: log.

    TODO Sprint 5: integrar com TelegramBot + Chatwoot inbox.
    Por ora so loga localmente (nao quebra se Telegram offline).
    """
    logger.error("DEAD_MANS_SWITCH_ALERT: %s", message)
