"""Service stale_detector - flagga atendimentos parados.

Workflow N8N #23 chama /api/v1/cron/stale-detector a cada 5min. Esse service
marca atendimentos com updated_at > threshold como 'stale' para que o
sistema (ou um humano) possa escalar.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.atendimento import Atendimento
from app.services.audit import AuditService

log = logging.getLogger(__name__)

STATUS_ABERTOS = ("aberto", "em_atendimento", "aguardando_cliente")


def mark_stale_atendimentos(db: Session, threshold_minutes: int = 30) -> dict[str, Any]:
    """Marca atendimentos parados como 'stale'.

    Args:
        db: sessao SQLAlchemy
        threshold_minutes: idade minima de updated_at pra ser considerado stale

    Returns:
        dict com 'scanned' (total analisado) e 'marked_stale' (quantos viraram stale)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

    rows = (
        db.execute(
            select(Atendimento).where(
                Atendimento.status.in_(STATUS_ABERTOS),
                Atendimento.updated_at < cutoff,
            )
        )
        .scalars()
        .all()
    )

    marked = 0
    for atendimento in rows:
        atendimento.status = "stale"
        marked += 1
        AuditService.log(
            db,
            actor_id="stale_detector",
            action="atendimento.stale",
            resource=f"atendimento:{atendimento.id}",
            actor_type="system",
            payload={
                "threshold_minutes": threshold_minutes,
                "updated_at": atendimento.updated_at.isoformat(),
            },
        )

    if marked:
        log.info("stale_detector: %d/%d atendimentos marcados stale", marked, len(rows))

    return {
        "scanned": len(rows),
        "marked_stale": marked,
        "threshold_minutes": threshold_minutes,
    }
