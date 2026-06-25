"""Adapter API → AuditService.log.

Camada fina entre Pydantic schemas (camada HTTP) e AuditService (chain builder).
Permite que endpoints POST /api/v1/audit/log criem entries de audit chain
via API, sem precisar importar AuditService direto nos handlers.

LGPD art. 37 — registro de tratamento via API.

D0.2 (2026-06-25): WF 23 LGPD Esqueci chama POST /audit/log para gravar
revogacao de consentimento. Antes deste adapter, WF 23 chamava endpoint
que NAO EXISTIA (404). Agora WF 23 grava audit log via API com chain
integrity preservada (HMAC + prev_hash automaticos via AuditService.log).

NAO mexer em services/audit.py — chain builder eh intocavel.
Este adapter apenas traduz schema → kwargs de AuditService.log.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogCreate
from app.services.audit import AuditService


def create_audit_log_entry(db: Session, entry: AuditLogCreate) -> AuditLog:
    """Cria entry de audit log via AuditService (chain + HMAC automaticos).

    Args:
        db: Sessao SQLAlchemy (caller gerencia transacao).
        entry: Schema validado (AuditLogCreate) com actor/action/resource/payload/canal/ip/...

    Returns:
        AuditLog inserido (com hash, prev_hash, hmac_signature preenchidos).

    Raises:
        ValueError: se actor_id/action/resource forem vazios (validacao extra de
            seguranca alem do Pydantic — defense in depth).
    """
    # Defense in depth — Pydantic ja valida, mas garantimos string nao-vazia
    # porque AuditLog.actor_id/action/resource sao NOT NULL no schema do banco.
    if not entry.actor_id or not entry.action or not entry.resource:
        raise ValueError(
            "AuditLogCreate requer actor_id, action e resource nao-vazios "
            "(validacao LGPD art. 37 — registro minimo de tratamento)."
        )

    return AuditService.log(
        db,
        actor_id=entry.actor_id,
        actor_type=entry.actor_type,
        action=entry.action,
        resource=entry.resource,
        payload=entry.payload,
        canal=entry.canal,
        ip=entry.ip,
        user_agent=entry.user_agent,
        request_id=entry.request_id,
    )


__all__ = ["create_audit_log_entry"]
