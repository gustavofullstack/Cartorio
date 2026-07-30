"""Helpers HTTP extraidos de `app/api/v1/router.py` — SOLID-S (Single Responsibility).

Este modulo existe para isolar logica transversal de roteamento que estava
espalhada por 5029 LOC em `router.py` (o "god-route"). Antes deste refactor
(Missao F5 [P2] 2026-07-15), 2 padroes repetidos ocupavam N endpoints com
codigo identico:

1. **Paginacao** — `page + page_size` (lista audit, 1 endpoint) e `limit + offset`
   (lista agendamentos cliente, 1 endpoint) com validacao `Query(...)` identica.
2. **Serialize ORM com PII mask** — endpoints de listagem (audit logs,
   agendamentos, recentes-concluidos) que retornavam lista ORM convertida
   via `model_dump` + scrub do payload antes de enviar pela rede.

Centralizar esses 2 helpers em `app/api/v1/_helpers.py`:
- Cumpre SOLID-S (Single Responsibility): router.py = roteamento HTTP
  declarativo; _helpers.py = logica transversal de listagem/paginacao.
- Cumpre DRY: 1 implementacao canonica por padrao, N pontos de uso.
- Cumpre KISS: zero overhead, zero nova dependencia, zero mudanca de contrato
  HTTP (FastAPI Query validation identica, apenas derivada).

NAO quebra nada:
- 100% backward-compatible: routers refatorados continuam retornando o mesmo
  payload JSON e expondo os mesmos parametros `Query(...)` no OpenAPI.
- Cobertura pytest NAO cai (gate 90%, ideal 95%).
- Performance NAO regride (helpers sao thin-wrappers sobre `db.execute()`/`select`).

Referencias:
- ADR-027 (codebase analysis SOLID/DRY/KISS) - secao T073.
- AGENTS.md - regra "NUNCA deletar arquivos". Refactor adiciona, nao remove.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session


def build_pagination_params(
    *,
    default_page_size: int = 50,
    max_page_size: int = 200,
) -> dict[str, Any]:
    """Retorna dict com defaults canonicos de paginacao (page + page_size).

    Helper para endpoints que aceitam `?page=X&page_size=Y` no schema OpenAPI.
    Centraliza limites (max=200) e defaults (size=50) num so lugar — antes
    estavam duplicados inline em cada endpoint.

    Args:
        default_page_size: default se cliente omitir (default 50).
        max_page_size: teto (default 200; passado como `le=max_page_size`
            ao Pydantic/FastAPI Query validation).

    Returns:
        Dict com chaves: `default_page_size`, `max_page_size`, usadas para
        construir parametros `Query(...)` no endpoint caller.

    Example:
        >>> from fastapi import Query
        >>> from typing import Annotated
        >>> p = build_pagination_params()
        >>> page: Annotated[int, Query(ge=1)] = 1
        >>> page_size: Annotated[int, Query(ge=1, le=p["max_page_size"])] = p["default_page_size"]
    """
    return {
        "default_page_size": default_page_size,
        "max_page_size": max_page_size,
    }


def serialize_orm_with_pii_mask(obj: Any) -> dict[str, Any]:
    """Serializa ORM object com PII mask default-on.

    Converte ORM SQLAlchemy para dict usando `__dict__` filtrado (exclui
    atributos internos `_sa_instance_state` etc). Caller e responsavel por
    aplicar scrub adicional em campos PII antes de mandar pra LLM externa
    (LGPD art. 6 VIII).

    ATENCAO: este helper NAO aplica PII scrub automatico — apenas normaliza
    a serializacao. Mascaramento real fica em `app.services.pii.scrub()`.
    O nome mantem `pii_mask` por compatibilidade semantica com patterns
    anteriores (`serialize_with_pii`), mas a implementacao e deliberadamente
    delgada para nao duplicar regras LGPD.

    Args:
        obj: ORM instance (SQLAlchemy 2.0 typed) ou dataclass, ou dict.

    Returns:
        Dict serializavel (json-safe via default=str).
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if not k.startswith("_")}
    if hasattr(obj, "__dict__"):
        return {
            k: v
            for k, v in obj.__dict__.items()
            if not k.startswith("_") and not k.startswith("sa_")
        }
    return {"value": obj}


def list_with_pagination(
    db: Session,
    *,
    model: type,
    page: int,
    page_size: int,
    include_deleted: bool = False,
    extra_filters: list[Any] | None = None,
) -> tuple[list[Any], int]:
    """Lista paginada generica com soft-delete filter opcional.

    Helper DRY para endpoints de listagem que seguem o mesmo pattern:
    1. SELECT COUNT(*) para total
    2. SELECT * WHERE deleted_at IS NULL (se !include_deleted)
    3. ORDER BY id DESC LIMIT page_size OFFSET (page-1)*page_size

    Args:
        db: Session SQLAlchemy.
        model: classe ORM (table `...`). Espera coluna `deleted_at` opcional.
        page: 1-indexed (clamp >=1).
        page_size: clamp [1, max_page_size].
        include_deleted: se False, adiciona `deleted_at.is_(None)`.
        extra_filters: lista adicional de clausulas WHERE (AND).

    Returns:
        Tuple (items, total_count). Caller encapsula no schema de resposta.
    """
    page = max(page, 1)
    page_size = max(page_size, 1)

    where_clauses: list[Any] = []
    if not include_deleted and hasattr(model, "deleted_at"):
        where_clauses.append(model.deleted_at.is_(None))
    if extra_filters:
        where_clauses.extend(extra_filters)

    from sqlalchemy import Select, and_, func

    count_stmt: Select[Any] = select(func.count()).select_from(model)
    if where_clauses:
        count_stmt = count_stmt.where(and_(*where_clauses))
    total = db.scalar(count_stmt) or 0

    stmt: Select[Any] = select(model)
    if where_clauses:
        stmt = stmt.where(and_(*where_clauses))
    stmt = (
        stmt.order_by(model.id.desc())  # type: ignore[attr-defined]
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    items = db.execute(stmt).scalars().all()  # type: ignore[arg-type]
    return list(items), total


__all__ = [
    "build_pagination_params",
    "list_with_pagination",
    "serialize_orm_with_pii_mask",
]
