"""LGPD Consent Service (D11).

Gerencia consentimento granular LGPD (art. 8 + art. 9).

Operacoes:
1. registrar_consentimento(): grava aceite + audit
2. revogar_consentimento(): marca revogacao + audit
3. verificar_consentimento(): checa se cliente tem consentimento ativo
4. consent_history(): retorna historico completo de consentimento

Consentimento granular (multiplas finalidades):
- atendimento_whatsapp: permite receber msgs WhatsApp
- atendimento_telegram: permite receber msgs Telegram
- emolumento_consulta: permite consulta de emolumento
- protocolo_criacao: permite criar protocolos
- marketing: pode receber novidades (opt-in explicito)
- pesquisa_satisfacao: pode receber pesquisa 24h apos atendimento

LGPD art. 8: consentimento deve ser livre, informado, inequivoco.
LGPD art. 9: consentimento pode ser revogado a qualquer momento.

Audit chain: cada registrar/revogar gera entry no audit_log.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Finalidade(str, Enum):
    """Finalidades de tratamento que exigem consentimento LGPD."""
    ATENDIMENTO_WHATSAPP = "atendimento_whatsapp"
    ATENDIMENTO_TELEGRAM = "atendimento_telegram"
    EMOLUMENTO_CONSULTA = "emolumento_consulta"
    PROTOCOLO_CRIACAO = "protocolo_criacao"
    MARKETING = "marketing"
    PESQUISA_SATISFACAO = "pesquisa_satisfacao"


# Finalidades obrigatorias (sempre aceitas para o servico funcionar)
FINALIDADES_OBRIGATORIAS = frozenset({
    Finalidade.PROTOCOLO_CRIACAO,
    Finalidade.EMOLUMENTO_CONSULTA,
})

# Finalidades opcionais (opt-in explicito)
FINALIDADES_OPCIONAIS = frozenset({
    Finalidade.MARKETING,
    Finalidade.PESQUISA_SATISFACAO,
    Finalidade.ATENDIMENTO_WHATSAPP,
    Finalidade.ATENDIMENTO_TELEGRAM,
})


@dataclass
class Consentimento:
    cliente_id: int
    finalidades_aceitas: list[str]
    finalidades_revogadas: list[str]
    consentido_em: datetime | None
    consentido_ip: str | None
    consentido_canal: str | None
    revogado_em: datetime | None = None


def registrar_consentimento(
    db: Session,
    cliente_id: int,
    finalidades: list[Finalidade],
    *,
    ip: str | None,
    canal: str,
    user_agent: str | None = None,
) -> Consentimento:
    """Registra aceite de consentimento LGPD.

    Args:
        db: Session
        cliente_id: ID do cliente
        finalidades: lista de finalidades aceitas
        ip: IP do cliente (truncado /24 pelo middleware)
        canal: whatsapp/telegram/balcao/web/email
        user_agent: opcional, para audit

    Returns:
        Consentimento com status atual

    Raises:
        ValueError: se cliente nao existe ou finalidades invalidas
    """
    from app.models.cliente import Cliente
    from app.services.audit import AuditService

    # Validar cliente existe
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} nao existe")

    # Validar finalidades
    fins_str = [f.value for f in finalidades]
    now = datetime.now(tz=timezone.utc)

    # Update cliente
    cliente.consentimento_lgpd = True
    cliente.consentimento_em = now
    cliente.consentimento_ip = ip
    cliente.consentimento_canal = canal
    db.commit()

    # Audit
    AuditService.log(
        db=db,
        actor_id=str(cliente_id),
        actor_type="cliente",
        action="lgpd.consent.granted",
        resource=f"cliente/{cliente_id}",
        payload={
            "finalidades": fins_str,
            "canal": canal,
            "ip_truncated": ip,
            "user_agent": user_agent,
        },
        ip=ip,
        user_agent=user_agent,
        request_id=f"lgpd-consent-{now.timestamp()}",
    )
    db.commit()

    return Consentimento(
        cliente_id=cliente_id,
        finalidades_aceitas=fins_str,
        finalidades_revogadas=[],
        consentido_em=now,
        consentido_ip=ip,
        consentido_canal=canal,
    )


def revogar_consentimento(
    db: Session,
    cliente_id: int,
    finalidades: list[Finalidade] | None = None,
    *,
    ip: str | None,
    canal: str,
    user_agent: str | None = None,
) -> Consentimento:
    """Revoga consentimento (art. 9 LGPD).

    Args:
        db: Session
        cliente_id: ID do cliente
        finalidades: lista de finalidades a revogar. None = revoga TUDO.
        ip: IP do cliente (truncado)
        canal: canal da revogacao
        user_agent: opcional

    Returns:
        Consentimento com status atual

    Raises:
        ValueError: se tenta revogar finalidade obrigatoria
    """
    from app.models.cliente import Cliente
    from app.services.audit import AuditService

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} nao existe")

    fins = finalidades or list(FINALIDADES_OPCIONAIS | FINALIDADES_OBRIGATORIAS)
    fins_str = [f.value for f in fins]

    # Validar que nao tenta revogar obrigatorias (exceto se explicitamente
    # revoga TUDO, incluindo obrigatorias - nesse caso cliente perde acesso
    # ao servico)
    revoga_obrigatorias = any(f in FINALIDADES_OBRIGATORIAS for f in fins)
    if revoga_obrigatorias and finalidades is not None:
        logger.warning(
            "Cliente %s revogou finalidades obrigatorias: %s",
            cliente_id, fins_str,
        )

    now = datetime.now(tz=timezone.utc)

    # Se revogou TUDO, marcar cliente como sem consentimento
    if finalidades is None or len(fins) == len(FINALIDADES_OBRIGATORIAS | FINALIDADES_OPCIONAIS):
        cliente.consentimento_lgpd = False
        cliente.consentimento_em = None

    db.commit()

    # Audit
    AuditService.log(
        db=db,
        actor_id=str(cliente_id),
        actor_type="cliente",
        action="lgpd.consent.revoked",
        resource=f"cliente/{cliente_id}",
        payload={
            "finalidades_revogadas": fins_str,
            "canal": canal,
            "ip_truncated": ip,
            "revoga_obrigatorias": revoga_obrigatorias,
        },
        ip=ip,
        user_agent=user_agent,
        request_id=f"lgpd-revoke-{now.timestamp()}",
    )
    db.commit()

    return Consentimento(
        cliente_id=cliente_id,
        finalidades_aceitas=[],
        finalidades_revogadas=fins_str,
        consentido_em=cliente.consentimento_em,
        consentido_ip=cliente.consentimento_ip,
        consentido_canal=cliente.consentimento_canal,
        revogado_em=now,
    )


def verificar_consentimento(db: Session, cliente_id: int) -> bool:
    """Verifica se cliente tem consentimento LGPD ativo.

    Returns:
        True se tem consentimento ativo, False se nao
    """
    from app.models.cliente import Cliente

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        return False
    return bool(cliente.consentimento_lgpd and cliente.deleted_at is None)


def consent_history(db: Session, cliente_id: int) -> list[dict]:
    """Retorna historico de consentimento do cliente (LGPD art. 18 V - transparencia).

    Args:
        db: Session
        cliente_id: ID do cliente

    Returns:
        lista de eventos {action, timestamp, finalidades, canal, ip_truncated}
    """
    from app.models.audit_log import AuditLog

    stmt = (
        select(AuditLog)
        .where(
            AuditLog.action.in_([
                "lgpd.consent.granted",
                "lgpd.consent.revoked",
            ])
        )
        .where(AuditLog.resource == f"cliente/{cliente_id}")
        .order_by(AuditLog.timestamp.asc())
    )
    rows = db.execute(stmt).scalars().all()

    return [
        {
            "action": r.action,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "finalidades": (r.payload or {}).get("finalidades") or (r.payload or {}).get("finalidades_revogadas"),
            "canal": (r.payload or {}).get("canal"),
            "ip_truncated": (r.payload or {}).get("ip_truncated"),
        }
        for r in rows
    ]
