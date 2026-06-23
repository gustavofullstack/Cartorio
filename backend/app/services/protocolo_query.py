"""Service de query de Protocolos.

Usado pelo N8N workflow #25 (protocolo concluido -> envia PDF via WhatsApp).
Tambem usado pelo dashboard DPO para monitorar transicoes recentes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.protocolo import Protocolo


@dataclass(frozen=True)
class ProtocoloRecente:
    """Item de protocolo concluido recentemente (denormalizado pra N8N)."""

    id: int
    numero: str
    status: str
    tipo: str
    valor_total: float | None
    canal_origem: str
    cliente_nome: str
    cliente_telefone: str | None
    concluído_em: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "numero": self.numero,
            "status": self.status,
            "tipo": self.tipo,
            "valor_total": self.valor_total,
            "canal_origem": self.canal_origem,
            "cliente": {
                "nome": self.cliente_nome,
                "telefone": self.cliente_telefone,
            },
            "concluido_em": self.concluído_em.isoformat() if self.concluído_em else None,
        }


def listar_protocolos_recentes_concluidos(
    db: Session,
    *,
    minutos: int = 10,
    limit: int = 50,
) -> list[ProtocoloRecente]:
    """Lista protocolos que mudaram para status=concluido nos ultimos N minutos.

    Args:
        db: SQLAlchemy session.
        minutos: janela de tempo (default 10min, suficiente para cron 5min).
        limit: maximo de items (default 50, evita paginacao).

    Returns:
        Lista de ProtocoloRecente ordenados por concluded_at DESC.

    Note:
        Como nao temos coluna `concluded_at` no model, usamos `updated_at`.
        Para distinguir "concluido agora" de "atualizado por outra razao",
        filtramos por `status='concluido'` E `updated_at >= cutoff`.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutos)

    rows = (
        db.query(Protocolo)
        .join(Cliente, Protocolo.cliente_id == Cliente.id)
        .filter(
            Protocolo.status == "concluido",
            Protocolo.updated_at >= cutoff,
        )
        .order_by(Protocolo.updated_at.desc())
        .limit(limit)
        .all()
    )

    return [
        ProtocoloRecente(
            id=p.id,
            numero=p.numero,
            status=p.status,
            tipo=p.tipo,
            valor_total=float(p.valor_total) if p.valor_total is not None else None,
            canal_origem=p.canal_origem,
            cliente_nome=p.cliente.nome if p.cliente else "DESCONHECIDO",
            cliente_telefone=None,  # Cliente model nao tem telefone (hash only)
            concluído_em=p.updated_at,  # proxy: updated_at = concluded_at aproximado
        )
        for p in rows
    ]


__all__ = ["ProtocoloRecente", "listar_protocolos_recentes_concluidos"]
