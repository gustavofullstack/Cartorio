"""Pacote de repositories — padrao DRY para acesso a dados.

A19 SQUAD A: BaseRepository com operacoes CRUD + soft delete.

Por que BaseRepository:
- DRY: routers repetem `db.query(Model).filter(...).all()` centenas
  de vezes. Repository centraliza os patterns.
- Testabilidade: routers recebem repo injetado, tests mockam.
- LGPD-by-default: `find_active()` ja aplica o filtro de
  `deleted_at IS NULL`. Hard find disponivel via flag explicita.

Models compativeis: qualquer classe com SoftDeleteMixin.

Uso tipico (em um router):
    from app.repositories.base import BaseRepository
    from app.models.cliente import Cliente

    class ClienteRepository(BaseRepository[Cliente]):
        def __init__(self, db: Session) -> None:
            super().__init__(Cliente, db)

    @router.get("/clientes")
    def list_clientes(repo: ClienteRepository = Depends(...)):
        return repo.find_active()

Cenarios cobertos:
- soft_delete(obj): marca timestamp UTC
- restore(obj): zera timestamp
- find_active(): query com filtro padrao
- find_including_deleted(): bypass admin (gated por permissao)
- find_by_id(id, include_deleted=False): busca por PK
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Query, Session

from app.models.mixins import SoftDeleteMixin

T = TypeVar("T", bound=SoftDeleteMixin)


class BaseRepository(Generic[T]):
    """Repository generico para entidades com SoftDeleteMixin.

    Subclasses devem chamar super().__init__(model, db) e podem
    adicionar queries especificas (e.g. `find_by_cpf_hash` em
    ClienteRepository).

    Nao eh obrigatorio usar este repository — services legados
    continuam usando `db.query(...)` diretamente. Repository eh
    a RECOMENDACAO para novos endpoints (consistencia + LGPD-by-default).
    """

    model: type[T]

    def __init__(self, model: type[T], db: Session) -> None:
        """Inicializa com o modelo e a session.

        Args:
            model: classe do modelo (subclasse de SoftDeleteMixin).
            db: SQLAlchemy session ativa.
        """
        self.model = model
        self.db = db

    # ------------------------------------------------------------------
    # Soft delete operations
    # ------------------------------------------------------------------

    def soft_delete(self, obj: T) -> T:
        """Marca `obj` como deletado (UPDATE deleted_at = utcnow).

        Idempotente: se ja deletado, NAO sobrescreve timestamp.
        Requer commit() explicito pelo caller (repository NAO controla
        transacao — caller decide escopo).

        Args:
            obj: instancia carregada do modelo.

        Returns:
            Mesmo objeto, com `deleted_at` setado.
        """
        obj.soft_delete()
        return obj

    def soft_delete_by_id(self, id: int) -> T | None:
        """Soft delete por ID (conveniencia).

        Returns:
            Objeto soft-deletado, ou None se nao encontrado.
        """
        obj = self.db.get(self.model, id)
        if obj is None:
            return None
        return self.soft_delete(obj)

    def restore(self, obj: T) -> T:
        """Desfaz soft delete (UPDATE deleted_at = NULL).

        Args:
            obj: instancia soft-deletada.

        Returns:
            Mesmo objeto, com `deleted_at` zerado.
        """
        obj.restore()
        return obj

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def find_active(self) -> Query:
        """Lista entidades NAO soft-deletadas (`deleted_at IS NULL`).

        Returns:
            SQLAlchemy Query (caller aplica .all()/.first()/.count()).
        """
        return self.db.query(self.model).filter(self.model.deleted_at.is_(None))

    def find_including_deleted(self) -> Query:
        """Lista TODAS as entidades (incluindo soft-deletadas).

        Endpoint admin-only. Caller DEVE checar permissao.

        Returns:
            SQLAlchemy Query.
        """
        return self.db.query(self.model)

    def find_by_id(self, id: int, *, include_deleted: bool = False) -> T | None:
        """Busca por PK.

        Args:
            id: primary key.
            include_deleted: True permite retornar soft-deletados.
                False (default) -> retorna None se soft-deletado.

        Returns:
            Instancia ou None.
        """
        obj = self.db.get(self.model, id)
        if obj is None:
            return None
        if not include_deleted and obj.deleted_at is not None:
            return None
        return obj

    def find_deleted(self) -> Query:
        """Lista entidades SOFT-DELETADAS (incluindo timestamp).

        Util para relatorios LGPD, jobs de retencao 5y, auditoria.

        Returns:
            Query filtrando `deleted_at IS NOT NULL`.
        """
        return self.db.query(self.model).filter(self.model.deleted_at.isnot(None))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def count_active(self) -> int:
        """Conta entidades NAO deletadas (count otimizado)."""
        return (
            self.db.query(self.model)
            .filter(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
            .count()
        )


__all__ = ["BaseRepository"]
