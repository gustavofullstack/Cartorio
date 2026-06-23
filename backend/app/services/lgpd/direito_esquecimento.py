"""Direito ao esquecimento (LGPD art. 18 VI) - hard ou soft delete de Cliente.

Decisao arquitetural: ver ADR-018.

Regras:
- Cliente SEM protocolo (nenhum ato cartorario) -> HARD DELETE
  (remove do DB; LGPD permite, Provimento CNJ 74/2018 nao se aplica)
- Cliente COM protocolo (>= 1 ato) -> SOFT DELETE
  (anonimiza PII nao-essencial, marca deleted_at, motivo_encerramento)
- Cliente ja soft-deleted -> 409 Conflict (idempotencia via checagem deleted_at)
- Cliente inexistente -> 404 Not Found

O service NAO emite audit log (delega isso ao router, que tem acesso ao
request.state para contexto completo).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente, MotivoEncerramento
from app.models.protocolo import Protocolo


class ClienteNotFoundError(Exception):
    """Cliente nao existe no DB."""


class ClienteJaRevogadoError(Exception):
    """Cliente ja foi encerrado (soft delete anterior)."""


@dataclass(frozen=True)
class DeleteResult:
    """Resultado do direito ao esquecimento."""

    cliente_id: int
    tipo: Literal["hard", "soft"]
    protocolos_ativos: int
    data_encerramento: datetime
    motivo: MotivoEncerramento


def _count_protocolos(db: Session, cliente_id: int) -> int:
    """Conta protocolos NAO cancelados/expirados vinculados ao cliente."""
    stmt = (
        select(func.count(Protocolo.id))
        .where(Protocolo.cliente_id == cliente_id)
        .where(Protocolo.status.notin_(["cancelado", "expirado"]))
    )
    return int(db.execute(stmt).scalar() or 0)


def _anonimiza_pii(cliente: Cliente) -> None:
    """Soft delete: anonimiza PII nao-essencial, preserva cpf_hash.

    O cpf_hash permanece porque:
    1. O hash chain do audit log precisa referenciar o cliente original.
    2. Sem o cpf_hash, perdemos a unicidade do cliente.
    3. A reversao (se necessaria) so eh possivel com DPO + ferramenta dedicada.
    """
    # Mantem os 8 primeiros chars do cpf_hash pra identificacao interna
    hash_prefix = cliente.cpf_hash[:8] if cliente.cpf_hash else "DESCONHECIDO"
    cliente.nome = f"TITULAR_REVOGADO_{hash_prefix}"
    cliente.email = None
    cliente.telefone_hash = None
    cliente.consentimento_lgpd = False
    # cpf_hash MANTEM (ver docstring)


def direito_esquecimento(
    db: Session,
    cliente_id: int,
    motivo: MotivoEncerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
) -> DeleteResult:
    """Aplica direito ao esquecimento (LGPD art. 18 VI) ao cliente.

    Args:
        db: SQLAlchemy session.
        cliente_id: ID do cliente a ser encerrado.
        motivo: motivo do encerramento. Default REVOGACAO_CONSENTIMENTO.

    Returns:
        DeleteResult com tipo (hard/soft), contagem de protocolos, data.

    Raises:
        ClienteNotFoundError: cliente nao existe.
        ClienteJaRevogadoError: cliente ja soft-deleted (deleted_at != None).
    """
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ClienteNotFoundError(f"Cliente {cliente_id} nao encontrado")

    if cliente.deleted_at is not None:
        raise ClienteJaRevogadoError(
            f"Cliente {cliente_id} ja revogado em {cliente.deleted_at.isoformat()}"
        )

    protocolos_ativos = _count_protocolos(db, cliente_id)
    data_encerramento = datetime.now(timezone.utc)

    if protocolos_ativos == 0:
        # HARD DELETE: sem ato cartorario, sem obrigacao legal de reter.
        # Remove tambem protocolos cancelados/expirados do cliente (que ficaram
        # orfaos quando o cliente for apagado - FK sem CASCADE).
        protocolos_orfaos = (
            db.query(Protocolo)
            .filter(Protocolo.cliente_id == cliente_id)
            .filter(Protocolo.status.in_(["cancelado", "expirado"]))
            .all()
        )
        for p in protocolos_orfaos:
            db.delete(p)
        db.delete(cliente)
        db.commit()
        return DeleteResult(
            cliente_id=cliente_id,
            tipo="hard",
            protocolos_ativos=0,
            data_encerramento=data_encerramento,
            motivo=motivo,
        )

    # SOFT DELETE: cliente tem protocolo, anonimiza PII nao-essencial.
    _anonimiza_pii(cliente)
    cliente.deleted_at = data_encerramento
    cliente.motivo_encerramento = motivo
    db.commit()
    db.refresh(cliente)

    return DeleteResult(
        cliente_id=cliente_id,
        tipo="soft",
        protocolos_ativos=protocolos_ativos,
        data_encerramento=data_encerramento,
        motivo=motivo,
    )


__all__ = [
    "ClienteJaRevogadoError",
    "ClienteNotFoundError",
    "DeleteResult",
    "direito_esquecimento",
]
