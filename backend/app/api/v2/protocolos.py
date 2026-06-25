"""GET /api/v2/protocolos — listagem com cursor pagination Relay-style (A24.3).

API v2 quebra de v1:
- offset/limit v1 -> cursor (opaco base64) v2
- Envelope flat v1 -> envelope Relay v2

LGPD art. 37: response NAO expoe PII (apenas IDs).

Auth: X-API-Key (mesma v1). JWT sera adicionado em A24.x.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.db import get_db
from app.models.protocolo import Protocolo
from app.services.cursor import encode_cursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protocolos", tags=["v2", "protocolos"])


# ============================================================================
# Schemas (Pydantic v2)
# ============================================================================


class ProtocoloV2Node(BaseModel):
    """Node do protocolo LGPD-safe."""

    id: int
    numero: str
    cliente_id: int
    tipo: str
    status: str
    valor_total: Decimal | None = None
    prazo_dias: int | None = None
    previsao_conclusao: str | None = None
    concluido_em: str | None = None


class Edge(BaseModel):
    cursor: str
    node: ProtocoloV2Node


class PageInfo(BaseModel):
    has_next_page: bool
    end_cursor: str | None = None


class ProtocolosV2Response(BaseModel):
    edges: list[Edge]
    page_info: PageInfo
    total_count: int


# ============================================================================
# Endpoint
# ============================================================================


@router.get(
    "",
    summary="Lista protocolos (v2, cursor pagination)",
    description=(
        "Lista protocolos com paginacao Relay-style (edges + pageInfo). "
        "Filtros: status, cliente_id, tipo. Ordenacao estavel por id ASC."
    ),
    response_model=ProtocolosV2Response,
    response_description="Lista de protocolos paginada.",
)
async def listar_protocolos_v2(
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)],
    first: int = Query(default=20, ge=1, le=100, description="Max itens por pagina (1-100)."),
    after: str | None = Query(default=None, description="Cursor opaque da pagina anterior."),
    status: str | None = Query(default=None, description="Filtro por status."),
    cliente_id: int | None = Query(default=None, description="Filtro por cliente_id."),
    tipo: str | None = Query(default=None, description="Filtro por tipo."),
) -> dict[str, Any]:
    """Lista protocolos com cursor pagination (Relay-style)."""
    from app.services.cursor import decode_cursor_safe

    stmt = select(Protocolo).order_by(Protocolo.id.asc())

    if status:
        stmt = stmt.where(Protocolo.status == status)
    if cliente_id is not None:
        stmt = stmt.where(Protocolo.cliente_id == cliente_id)
    if tipo:
        stmt = stmt.where(Protocolo.tipo == tipo)

    if after:
        decoded = decode_cursor_safe(after, "id_after")
        if decoded is not None:
            stmt = stmt.where(Protocolo.id > decoded)

    stmt = stmt.limit(first + 1)
    rows = list(db.execute(stmt).scalars().all())

    has_next_page = len(rows) > first
    rows = rows[:first]

    edges = [
        Edge(
            cursor=encode_cursor({"id_after": p.id}),
            node=ProtocoloV2Node(
                id=p.id,
                numero=p.numero,
                cliente_id=p.cliente_id,
                tipo=p.tipo,
                status=p.status,
                valor_total=p.valor_total,
                prazo_dias=p.prazo_dias,
                previsao_conclusao=p.previsao_conclusao.isoformat()
                if p.previsao_conclusao
                else None,
                concluido_em=p.concluido_em.isoformat() if p.concluido_em else None,
            ),
        )
        for p in rows
    ]

    end_cursor = edges[-1].cursor if edges and has_next_page else None

    # total_count respeitando filtros
    count_stmt = select(func.count(Protocolo.id))
    if status:
        count_stmt = count_stmt.where(Protocolo.status == status)
    if cliente_id is not None:
        count_stmt = count_stmt.where(Protocolo.cliente_id == cliente_id)
    if tipo:
        count_stmt = count_stmt.where(Protocolo.tipo == tipo)
    total_count = int(db.execute(count_stmt).scalar_one() or 0)

    return ProtocolosV2Response(
        edges=edges,
        page_info=PageInfo(has_next_page=has_next_page, end_cursor=end_cursor),
        total_count=total_count,
    ).model_dump(mode="json")