"""Base declarativa compartilhada."""

from datetime import UTC, datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base de todos os modelos do cartorio."""


def utc_now_naive() -> datetime:
    """Retorna o instante atual em UTC sem ``tzinfo`` para colunas ``TIMESTAMP`` legadas.

    As migrations existentes usam ``DateTime`` sem timezone. Manter o valor
    naive evita uma mudanca silenciosa de schema, mas calcular primeiro em UTC
    conserva a semantica explicita e substitui ``datetime.utcnow()``, que foi
    depreciado no Python 3.12.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now_naive, onupdate=utc_now_naive, nullable=False
    )


__all__ = ["Base", "TimestampMixin", "utc_now_naive"]
