"""Mixins SQLAlchemy compartilhados entre modelos do cartorio.

A19 SQUAD A: SoftDeleteMixin — padrao global de soft delete.

Por que soft delete (LGPD + audit chain):
- LGPD art. 18 V: revogacao de consentimento NAO remove historico imediato;
  retencao minima legal se aplica (Provimento CNJ 74/2018 para clientes
  com protocolo).
- Audit chain SHA256 precisa de evidencia historica para verificar
  integridade retroativa. Hard delete quebra a chain.
- Corregedoria/ANPD podem exigir relatorio de transacoes encerradas.

Como usar:
    from sqlalchemy.orm import Mapped, mapped_column
    from app.models.mixins import SoftDeleteMixin

    class MinhaEntidade(Base, SoftDeleteMixin):
        __tablename__ = "minha_entidade"
        id: Mapped[int] = mapped_column(primary_key=True)
        nome: Mapped[str] = ...

    obj = db.get(MinhaEntidade, 1)
    obj.soft_delete()  # seta deleted_at = utcnow()
    obj.restore()      # seta deleted_at = None
    obj.is_deleted     # bool

O query helper `query_active(db, MinhaEntidade)` aplica o filtro
padrao `WHERE deleted_at IS NULL`. Para bypass admin use
`query_including_deleted(db, MinhaEntidade)`.

Tabelas que DEVEM ter SoftDeleteMixin (dominio):
- clientes, protocolos, conversas, documentos, agendamentos,
  atendimentos, webhook_events

Tabelas que NAO devem ter (system / audit):
- audit_log (integridade da hash chain)
- outbox_messages (DLQ — semantica de retry)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Select
from sqlalchemy.orm import Mapped, Query, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SoftDeleteMixin:
    """Adiciona coluna `deleted_at` + helpers de soft delete.

    A coluna e nullable=True com default=None. Soft delete seta o
    timestamp UTC; restore volta pra None.

    Indices: criar `CREATE INDEX ix_<tabela>_deleted_at
    ON <tabela> (deleted_at)` na migration. Partial index
    `WHERE deleted_at IS NULL` eh preferivel (queries ativas sempre
    filtram por IS NULL, economiza espaco em DB grandes).
    """

    # Use DateTime naive (UTC) — match migrations existentes (TIMESTAMP NULL).
    # LGPD/audit chain normaliza timestamp via `datetime.now(timezone.utc)`
    # + remove tzinfo antes de persistir. Documentado em ADR-018.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """True se soft-deletado."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Marca o registro como deletado (NUNCA remove do DB).

        Idempotente: chamar 2x NAO sobrescreve o primeiro timestamp.
        Para mudar o motivo, use `restore()` + `soft_delete()`.

        O timestamp gravado eh UTC naive (match com migration `TIMESTAMP NULL`
        ja aplicada em prod). Caller que precisa de offset-aware faz
        `obj.deleted_at.replace(tzinfo=timezone.utc)`.
        """
        if self.deleted_at is None:
            self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Desfaz soft delete (deleted_at=None)."""
        self.deleted_at = None


def query_active(db: "Session", model: type[SoftDeleteMixin]) -> Query:
    """Query padrao filtrando soft-deletados.

    Substitui `db.query(Model)` em servicos de leitura, garantindo
    que registros soft-deletados nao vazem.

    Args:
        db: SQLAlchemy session.
        model: classe que herda SoftDeleteMixin.

    Returns:
        Query com `WHERE deleted_at IS NULL` aplicado.

    Example:
        >>> clientes_ativos = query_active(db, Cliente).all()
    """
    return db.query(model).filter(model.deleted_at.is_(None))


def query_including_deleted(db: "Session", model: type[SoftDeleteMixin]) -> Query:
    """Query SEM filtro — inclui soft-deletados (uso ADMIN).

    Endpoint gated por permissao. NUNCA expor pra cliente final.
    """
    return db.query(model)


def select_active(model: type[SoftDeleteMixin]) -> Select:
    """SELECT padrao filtrando soft-deletados (estilo SQLAlchemy 2.0).

    Para queries que usam `db.execute(select(...))` em vez de
    `db.query(...)`.
    """
    return Select(model).where(model.deleted_at.is_(None))


__all__ = [
    "SoftDeleteMixin",
    "query_active",
    "query_including_deleted",
    "select_active",
]
