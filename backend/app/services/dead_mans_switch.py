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


def send_alert(message: str, *, chat_id: str | None = None) -> bool:
    """Envia alerta via Telegram GRUPO PIETRA (Sprint 5 G6.B.T4).

    Args:
        message: texto do alerta.
        chat_id: chat ID do Telegram (default: GRUPO PIETRA).

    Returns:
        True se enviou com sucesso, False caso contrario (fail-open).
    """
    import os

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    target_chat_id = (
        chat_id
        or os.environ.get("TELEGRAM_GRUPO_PIEIRA_CHAT_ID")
        or os.environ.get("TELEGRAM_CHAT_ID")
    )

    # Fail-open: log sempre, mesmo se Telegram offline
    logger.error("DEAD_MANS_SWITCH_ALERT: %s", message)

    if not bot_token or not target_chat_id:
        logger.warning(
            "Telegram nao configurado (bot_token=%s, chat_id=%s). Apenas log.",
            bool(bot_token),
            bool(target_chat_id),
        )
        return False

    try:
        import httpx

        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": target_chat_id,
                "text": f"🚨 DEAD MAN'S SWITCH\n\n{message}",
                "parse_mode": "HTML",
            },
            timeout=5.0,
        )
        ok = resp.status_code == 200
        if not ok:
            logger.error(
                "Telegram alert failed: HTTP %s body=%s", resp.status_code, resp.text[:200]
            )
        return ok
    except Exception as exc:
        logger.error("Telegram alert exception: %s: %s", type(exc).__name__, exc)
        return False
