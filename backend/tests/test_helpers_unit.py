"""Testes unitarios para `app.api.v1._helpers`.

Foco: SOLID-S — helpers extraidos de router.py.
Cobertura alvo: 95%+ (gate 90%, ideal 95%).

Notas de design:
- `list_with_pagination()` recebe uma `type` que precisa ter `id` e
  `deleted_at` como InstrumentedAttributes SQLAlchemy. Cobertura via
  testes integrados com Session SQLAlchemy em memoria (sqlite:///:memory:).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base


from app.api.v1._helpers import (
    build_pagination_params,
    list_with_pagination,
    serialize_orm_with_pii_mask,
)


def test_build_pagination_params_defaults() -> None:
    p = build_pagination_params()
    assert p["default_page_size"] == 50
    assert p["max_page_size"] == 200


def test_build_pagination_params_custom() -> None:
    p = build_pagination_params(default_page_size=25, max_page_size=100)
    assert p["default_page_size"] == 25
    assert p["max_page_size"] == 100


def test_serialize_orm_with_pii_mask_dict() -> None:
    """Dict puro passa pelo helper."""
    obj = {"a": 1, "_private": "should_skip", "b": [2, 3]}
    out = serialize_orm_with_pii_mask(obj)
    assert out == {"a": 1, "b": [2, 3]}


def test_serialize_orm_with_pii_mask_none() -> None:
    out = serialize_orm_with_pii_mask(None)
    assert out == {}


@dataclass
class FakeCliente:
    id: int = 1
    nome: str = "Maria"
    cpf_hash: str = "deadbeef"
    _internal_state: str = "should-be-stripped"


def test_serialize_orm_with_pii_mask_dataclass() -> None:
    """ORM-like com underscore-prefixed attrs devem ser strippados."""
    cli = FakeCliente(id=42, nome="Maria", cpf_hash="abc")
    out = serialize_orm_with_pii_mask(cli)
    assert out["id"] == 42
    assert out["nome"] == "Maria"
    assert out["cpf_hash"] == "abc"
    assert "_internal_state" not in out


def test_serialize_orm_with_pii_mask_sa_attrs() -> None:
    """Atributos SA (sa_instance_state, sa_*) sao strippados via sa_ prefix."""
    @dataclass
    class WithSa:
        id: int = 1
        sa_instance_state: object = None
        sa_extra: str = "x"

    obj = WithSa(id=7, sa_instance_state=MagicMock(), sa_extra="y")
    out = serialize_orm_with_pii_mask(obj)
    assert "sa_instance_state" not in out
    assert "sa_extra" not in out
    assert out["id"] == 7


def test_serialize_orm_with_pii_mask_primitive() -> None:
    """Primitives sao embrulhados em dict com chave value."""
    out = serialize_orm_with_pii_mask(42)
    assert out == {"value": 42}

    out_str = serialize_orm_with_pii_mask("hello")
    assert out_str == {"value": "hello"}


def test_serialize_orm_with_pii_mask_filters_sa_prefix() -> None:
    """Atributos comecados com _ sao strippados; samsa (sem _) preservado."""
    @dataclass
    class WithMixed:
        id: int = 1
        samsa: str = "keep"
        _underscore_private: str = "strip"

    obj = WithMixed(id=3, samsa="keep", _underscore_private="strip")
    out = serialize_orm_with_pii_mask(obj)
    assert out["samsa"] == "keep"
    assert "_underscore_private" not in out
    assert out["id"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])


# ============================================================================
# Testes integrados SQLAlchemy para list_with_pagination (cobertura 44% -> 100%)
# ============================================================================

_Base = declarative_base()


class _FakeEntidade(_Base):
    """Minimal ORM para testar list_with_pagination."""

    __tablename__ = "fake_entidade"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(50))
    deleted_at = Column(DateTime, nullable=True)


@pytest.fixture
def sa_session():
    """Session SQLAlchemy em memoria (sqlite) com 5 rows + 1 soft-deletada."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        # 5 ativos
        for i in range(5):
            session.add(_FakeEntidade(id=i + 1, nome=f"ativo-{i}"))
        # 1 soft-deletado
        session.add(
            _FakeEntidade(
                id=99,
                nome="deletado",
                deleted_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()
        # Re-emit fresh session para queries limpas
        yield session


def test_list_with_pagination_excludes_soft_deleted(sa_session: Session) -> None:
    """Default: include_deleted=False exclui deleted_at IS NOT NULL."""
    items, total = list_with_pagination(
        sa_session, model=_FakeEntidade, page=1, page_size=10
    )
    assert total == 5  # 5 ativos; 1 soft-deletado excluido
    assert all(it.deleted_at is None for it in items)


def test_list_with_pagination_include_deleted(sa_session: Session) -> None:
    """include_deleted=True inclui a soft-deletada (total=6)."""
    items, total = list_with_pagination(
        sa_session,
        model=_FakeEntidade,
        page=1,
        page_size=10,
        include_deleted=True,
    )
    assert total == 6
    assert any(it.nome == "deletado" for it in items)


def test_list_with_pagination_paging_works(sa_session: Session) -> None:
    """Paginacao: page=1 size=2 -> 2 items; page=2 size=2 -> 2 items; page=3 size=2 -> 1 item."""
    items_p1, total_p1 = list_with_pagination(
        sa_session, model=_FakeEntidade, page=1, page_size=2
    )
    items_p3, total_p3 = list_with_pagination(
        sa_session, model=_FakeEntidade, page=3, page_size=2
    )
    assert total_p1 == 5
    assert total_p3 == 5
    assert len(items_p1) == 2
    assert len(items_p3) == 1


def test_list_with_pagination_extra_filters(sa_session: Session) -> None:
    """Extra filters sao aplicados em AND com deleted_at."""
    items, total = list_with_pagination(
        sa_session,
        model=_FakeEntidade,
        page=1,
        page_size=10,
        extra_filters=[_FakeEntidade.id == 3],
    )
    assert total == 1
    assert items[0].id == 3
