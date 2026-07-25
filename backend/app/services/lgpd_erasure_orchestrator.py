"""LGPD Erasure Orchestrator (D23).

Coordena o direito ao esquecimento completo (LGPD art. 18 IV/V) para um
titular, garantindo:

1. **Anonimizacao do cliente** (substitui nome/email/telefone por placeholders;
   preserva PK para integridade referencial com protocolos/historicos).
2. **Soft-delete das conversas** (marca deleted_at em conversas ativas).
3. **Audit log append-only** com hash chain PRESERVADO — NUNCA deletar entries.
4. **Idempotencia**: chamadas repetidas produzem o mesmo efeito final.

LGPD-by-design + Compliance:

- LGPD art. 18 IV/V: titular pode requisitar anonimizacao/elimineacao.
- LGPD art. 37: integridade do audit log deve ser MANTIDA (obrigacao legal).
- LGPD art. 6o VIII (prevencao): NUNCA deletar audit log (chain quebra).
- Provimento CNJ 74/2018: clientes com protocolo podem ser anonimizados apos
  janela de retencao (5 anos).

Workflow:
    erase_cliente(db, cliente_id=42, actor_id='dpo:gustavo')
    -> sucesso: cliente anonimizado + conversas soft-deleted + audit_id
    -> chamando 2x: idempotente (mesmo resultado, audit_log_id diferente)

Uso:
    from app.services.lgpd_erasure_orchestrator import erase_cliente

    result = erase_cliente(db, cliente_id=42, actor_id='dpo:gustavo')
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# Helpers — mascaramento PII reversivel-preservando-PK
# ============================================================================


_ANON_PLACEHOLDER_NOME = "[ANONIMIZADO art.18 V]"
_ANON_PLACEHOLDER_EMAIL = None  # None = vazio (LGPD-by-design)


def _anonimizar_cliente_row(
    db: Session,
    cliente_id: int,
    *,
    reversivel_ate: datetime | None,
) -> dict[str, Any]:
    """Anonimiza cliente no DB (D13 + D14). Preserva PK.

    Args:
        db: Session
        cliente_id: PK
        reversivel_ate: ate quando pode ser revertido (default: now + 30d)

    Returns:
        dict com `cliente_id`, `reversivel_ate`, `anonimizado` (bool)
        ou `erro` se cliente nao existe.
    """
    from app.models.cliente import Cliente

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        return {"erro": "cliente_nao_encontrado", "cliente_id": cliente_id}

    # Idempotencia: se ja anonimizado (deleted_at setado) e nome ja eh placeholder,
    # retorna no-op.
    if cliente.deleted_at is not None and cliente.nome.startswith("[ANON"):
        return {
            "cliente_id": cliente_id,
            "anonimizado": False,
            "idempotente": True,
            "ja_anonimizado": True,
        }

    # Substitui PII sensivel mantendo PK
    cliente.nome = _ANON_PLACEHOLDER_NOME
    cliente.email = _ANON_PLACEHOLDER_EMAIL  # type: ignore[assignment]
    cliente.telefone_hash = None  # type: ignore[assignment]
    # cpf_hash preservado (ja eh hash irreversivel LGPD-by-design)
    cliente.consentimento_lgpd = False
    cliente.deleted_at = datetime.now(tz=UTC).replace(tzinfo=None)
    if reversivel_ate is not None:
        cliente.lgpd_reversivel_ate = reversivel_ate.replace(tzinfo=None)

    return {
        "cliente_id": cliente_id,
        "anonimizado": True,
        "idempotente": False,
        "reversivel_ate": reversivel_ate.isoformat() if reversivel_ate else None,
    }


def _soft_delete_conversas(db: Session, cliente_id: int) -> dict[str, Any]:
    """Soft-deleta conversas do titular (marca deleted_at).

    Preserva todos os registros (audit, contagens) — apenas o deleted_at impede
    que aparecam em queries ativas.

    Returns:
        dict com {cliente_id, conversas_deleted, tabelas_afetadas}
    """
    from sqlalchemy import update

    from app.models.conversa import Conversa

    now = datetime.now(tz=UTC).replace(tzinfo=None)

    # Update em batch (nao pega todos pra memoria). Filtra deleted_at IS NULL
    # para preservar idempotencia.
    stmt = (
        update(Conversa)
        .where(Conversa.cliente_id == cliente_id)
        .where(Conversa.deleted_at.is_(None))
        .values(deleted_at=now)
    )
    result = db.execute(stmt)
    rowcount = int(getattr(result, "rowcount", 0) or 0)

    return {
        "cliente_id": cliente_id,
        "conversas_deleted": rowcount,
        "tabelas_afetadas": ["conversas"],
    }


def _audit_erasure(
    db: Session,
    *,
    cliente_id: int,
    actor_id: str,
    motivo: str,
    reversivel_ate: datetime | None,
    result_summary: dict[str, Any],
) -> int:
    """Registra erasure no audit log (LGPD art. 37 + cartorio-lgpd review).

    CRITICO: usa AuditService.log() para preservar hash chain (SHA256 + HMAC).
    Audit log NUNCA eh deletado.

    Returns:
        audit_log.id
    """
    from app.services.audit import AuditService

    audit_payload = {
        "cliente_id": cliente_id,
        "actor_id": actor_id,
        "motivo": motivo,
        "reversivel_ate": reversivel_ate.isoformat() if reversivel_ate else None,
        "result_summary": result_summary,
        "lgpd_article": "art. 18 IV/V",
        "orchestrator_version": "1.0",
    }
    audit_entry = AuditService.log(
        db,
        actor_id=actor_id,
        actor_type="dpo",
        action="lgpd.erasure.orchestrated",
        resource=f"cliente:{cliente_id}",
        payload=audit_payload,
    )
    return int(audit_entry.id)


# ============================================================================
# Orquestrador principal
# ============================================================================


@dataclass
class ErasureResult:
    """Resultado consolidado de uma operacao de erasure.

    Atributos:
        cliente_id: PK do titular
        cliente_anonimizado: True se cliente foi anonimizado nesta chamada
        idempotente: True se chamada eh no-op (cliente ja estava anonimizado)
        conversas_deleted: numero de conversas soft-deleted nesta chamada
        audit_log_id: ID da entry do audit log registrada
        reversivel_ate: timestamp limite para reversao (ou None)
        executado_em: timestamp do momento de execucao
    """

    cliente_id: int
    cliente_anonimizado: bool
    idempotente: bool
    conversas_deleted: int
    audit_log_id: int
    reversivel_ate: datetime | None
    executado_em: str
    erro: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def erase_cliente(
    db: Session,
    cliente_id: int,
    *,
    actor_id: str = "system:cartorio-dpo",
    motivo: str = "titular_solicitou",
    reversivel_ate: datetime | None = None,
) -> ErasureResult:
    """Orquestra erasure completo de um cliente (LGPD art. 18 IV/V).

    Fluxo (LGPD-by-design):
    1. Anonimiza cliente (substitui PII, preserva PK)
    2. Soft-delete conversas (marca deleted_at)
    3. Registra audit log (hash chain preservada)
    4. Commit

    Idempotencia: se chamado 2x no mesmo cliente ja anonimizado, retorna
    `idempotente=True` com `cliente_anonimizado=False` e `conversas_deleted=0`.

    Args:
        db: Session
        cliente_id: PK do cliente
        actor_id: quem esta executando (dpo:NOME, escrevente:ID, system:cartorio-dpo)
        motivo: motivo da solicitacao (titular_solicitou, retencao_expirada, etc)
        reversivel_ate: ate quando pode ser revertido (default: now + 30d)

    Returns:
        ErasureResult com o resultado detalhado

    Raises:
        ValueError: se cliente nao existe
    """
    if reversivel_ate is None:
        reversivel_ate = datetime.now(tz=UTC) + timedelta(days=30)

    # Etapa 1: anonimizar cliente (PK preservada)
    cliente_result = _anonimizar_cliente_row(db, cliente_id, reversivel_ate=reversivel_ate)
    if "erro" in cliente_result:
        # Cliente nao existe — vamos apenas logar e propagar
        return ErasureResult(
            cliente_id=cliente_id,
            cliente_anonimizado=False,
            idempotente=False,
            conversas_deleted=0,
            audit_log_id=0,
            reversivel_ate=None,
            executado_em=datetime.now(tz=UTC).isoformat(),
            erro=cliente_result["erro"],
        )

    # Etapa 2: soft-delete conversas (somente se cliente era novo a anonimizar)
    conversas_result: dict[str, Any] = {
        "cliente_id": cliente_id,
        "conversas_deleted": 0,
        "tabelas_afetadas": [],
    }
    if not cliente_result.get("idempotente"):
        conversas_result = _soft_delete_conversas(db, cliente_id)

    # Etapa 3: audit log (hash chain PRESERVADA — usa AuditService.log)
    summary = {
        "cliente": cliente_result,
        "conversas": conversas_result,
    }
    audit_id = _audit_erasure(
        db,
        cliente_id=cliente_id,
        actor_id=actor_id,
        motivo=motivo,
        reversivel_ate=reversivel_ate,
        result_summary=summary,
    )

    db.commit()

    logger.info(
        "LGPD erasure orchestrated: cliente_id=%s anonimizado=%s conversas_deleted=%s audit_id=%s",
        cliente_id,
        cliente_result.get("anonimizado"),
        conversas_result["conversas_deleted"],
        audit_id,
    )

    return ErasureResult(
        cliente_id=cliente_id,
        cliente_anonimizado=bool(cliente_result.get("anonimizado")),
        idempotente=bool(cliente_result.get("idempotente")),
        conversas_deleted=int(conversas_result["conversas_deleted"]),
        audit_log_id=audit_id,
        reversivel_ate=reversivel_ate,
        executado_em=datetime.now(tz=UTC).isoformat(),
        extra=summary,
    )


# ============================================================================
# Auditoria: verificar integridade apos erasure
# ============================================================================


def verify_audit_chain_intact(db: Session) -> tuple[bool, int]:
    """Re-exporta AuditService.verify_chain para conveniencia.

    Returns:
        (chain_ok, last_valid_position)
    """
    from app.services.audit import AuditService

    return AuditService.verify_chain(db)


def count_audit_entries_for_cliente(db: Session, cliente_id: int) -> int:
    """Conta entries de audit log referenciando esse cliente.

    Util para confirmar que o audit chain foi PRESERVADO apos erasure
    (audit_log NUNCA eh deletado, mesmo quando cliente eh anonimizado).
    """
    from sqlalchemy import func, select

    from app.models.audit_log import AuditLog

    stmt = select(func.count(AuditLog.id)).where(AuditLog.resource == f"cliente:{cliente_id}")
    return int(db.execute(stmt).scalar() or 0)


# ============================================================================
# Soft-delete generico (reuso para atendimentos / documentos)
# ============================================================================


def soft_delete_by_cliente(
    db: Session,
    *,
    table_name: str,
    cliente_id: int,
) -> int:
    """Soft-delete generico de tabela por cliente_id.

    Mantem o padrao: NAO remove do DB, apenas marca deleted_at. Usado como
    complemento do `erase_cliente()` para tabelas alem de conversas (ex:
    atendimentos, agendamentos).

    Args:
        db: Session
        table_name: nome da tabela (precisa ter coluna deleted_at + cliente_id)
        cliente_id: PK do cliente

    Returns:
        numero de rows soft-deleted (0 se tabela nao tem coluna deleted_at)
    """
    import re

    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    now = datetime.now(tz=UTC).replace(tzinfo=None)

    try:
        stmt = text(
            f"UPDATE {table_name} SET deleted_at = :now "
            "WHERE cliente_id = :cid AND deleted_at IS NULL"
        )
        result = db.execute(stmt, {"now": now, "cid": cliente_id})
        return int(getattr(result, "rowcount", 0) or 0)
    except Exception as e:
        logger.warning("soft_delete_by_cliente(%s, %s) falhou: %s", table_name, cliente_id, e)
        return 0


__all__ = [
    "ErasureResult",
    "count_audit_entries_for_cliente",
    "erase_cliente",
    "soft_delete_by_cliente",
    "verify_audit_chain_intact",
]
