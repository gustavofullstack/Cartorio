"""Dead Man's Switch admin endpoint (G6.A.T11).

Admin endpoint para inspecionar/controlar o dead man's switch audit log.
LGPD art. 37: detecta se a API parou de escrever no audit log (sinal de freeze/crash).

Operacoes:
1. GET /api/v1/admin/dead-mans-switch/status - status atual
2. POST /api/v1/admin/dead-mans-switch/heartbeat - heartbeat manual (reset timer)
3. GET /api/v1/admin/dead-mans-switch/history - historico de ultimas execucoes

Auth: X-API-Key (admin tier 30/min)

Refs:
- app/jobs/cron_dead_mans_switch.py (cron task A13)
- main.py startup hook

Modified by Gustavo Almeida + cartorio-dev — G6 wave 26.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.audit_log import AuditLog
from app.schemas.dead_mans_switch import (
    DeadMansSwitchHistory,
    DeadMansSwitchHistoryItem,
    DeadMansSwitchStatus,
)

router = APIRouter(prefix="/admin/dead-mans-switch", tags=["admin", "sre"])


@router.get(
    "/status",
    response_model=DeadMansSwitchStatus,
    summary="Status do dead man's switch (A13)",
)
def get_status(db: Session = Depends(get_db)) -> DeadMansSwitchStatus:
    """Retorna status atual: ultimo heartbeat, idade, threshold, alive?"""
    threshold_minutes = settings.audit_dead_mans_switch_minutes
    if threshold_minutes <= 0:
        return DeadMansSwitchStatus(
            enabled=False,
            threshold_minutes=0,
            last_heartbeat=None,
            age_seconds=None,
            is_alive=True,
            message="Dead man's switch desabilitado (AUDIT_DEAD_MANS_SWITCH_MINUTES=0)",
        )

    # Ultimo AuditLog entry
    last_log = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).first()

    if not last_log or not last_log.timestamp:
        return DeadMansSwitchStatus(
            enabled=True,
            threshold_minutes=threshold_minutes,
            last_heartbeat=None,
            age_seconds=None,
            is_alive=False,
            message="Nenhum audit log encontrado. API nunca escreveu ou tabela esta vazia.",
        )

    now = datetime.now(timezone.utc)
    last_ts = last_log.timestamp
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    age = now - last_ts
    age_seconds = int(age.total_seconds())
    threshold_seconds = threshold_minutes * 60
    is_alive = age_seconds < threshold_seconds

    return DeadMansSwitchStatus(
        enabled=True,
        threshold_minutes=threshold_minutes,
        last_heartbeat=last_ts.isoformat(),
        age_seconds=age_seconds,
        is_alive=is_alive,
        message=(
            f"Vivo: ultimo heartbeat {age_seconds}s atras (< {threshold_seconds}s)"
            if is_alive
            else f"MORTO: ultimo heartbeat {age_seconds}s atras (> {threshold_seconds}s threshold)"
        ),
    )


@router.post(
    "/heartbeat",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forca heartbeat manual (reset timer)",
)
def force_heartbeat(db: Session = Depends(get_db)) -> None:
    """Insere audit log de heartbeat manual. Reset timer do dead man's switch."""
    from app.services.audit import AuditService

    try:
        AuditService.log(
            db,
            actor_id="admin",
            action="heartbeat",
            resource="dead_mans_switch",
            payload={"forced_by": "admin", "ts": datetime.now(timezone.utc).isoformat()},
        )
        db.commit()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"erro": "HEARTBEAT_FAILED", "mensagem": str(exc)},
        ) from exc


@router.get(
    "/history",
    response_model=DeadMansSwitchHistory,
    summary="Historico dos ultimos heartbeats",
)
def get_history(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> DeadMansSwitchHistory:
    """Retorna ultimos N heartbeats (do audit log)."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail={"erro": "INVALID_LIMIT", "limit": limit})

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.resource == "dead_mans_switch")
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
        .all()
    )

    items = []
    for log in logs:
        # Tentar extrair timestamp do payload se for manual
        actor = "cron" if "interval" in (log.payload or {}) else "manual"
        items.append(
            DeadMansSwitchHistoryItem(
                timestamp=log.timestamp.isoformat() if log.timestamp else "",
                actor=actor,
                action=log.action or "heartbeat",
                hash=log.hash or "",
            )
        )

    return DeadMansSwitchHistory(total=len(items), items=items)
