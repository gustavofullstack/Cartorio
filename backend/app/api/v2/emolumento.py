"""GET /api/v2/emolumento/tabela — listagem da tabela oficial de emolumentos (A24.4).

Publico (sem auth necessario) — tabela eh dado publico de dominio cartorario.
Usa envelope Relay (edges + pageInfo) consistente com A24.2/A24.3.

LGPD: tabela NAO expoe PII. Apenas tipos + valores em BRL.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import require_cartorio_api_key
from app.services.cursor import encode_cursor
from app.services.emolumento import EMOLUMENTOS_2026

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emolumento", tags=["v2", "emolumento"])


# ============================================================================
# Schemas (Pydantic v2)
# ============================================================================


class EmolumentoV2Node(BaseModel):
    """Node da tabela de emolumento (LGPD-safe)."""

    tipo: str
    valor_base: Decimal
    gratuito: bool  # True se valor_base == 0 (registros, etc)


class Edge(BaseModel):
    cursor: str
    node: EmolumentoV2Node


class PageInfo(BaseModel):
    has_next_page: bool
    end_cursor: str | None = None


class EmolumentoTabelaV2Response(BaseModel):
    """Envelope Relay para tabela de emolumento."""

    edges: list[Edge]
    page_info: PageInfo
    total_count: int
    tabela_referencia: str  # ex: TABELA_2026_MG
    valido_ate: str  # ISO date


# ============================================================================
# Endpoint
# ============================================================================


@router.get(
    "/tabela",
    summary="Lista tabela oficial de emolumentos (v2, publico)",
    description=(
        "Retorna tabela de emolumentos vigente (MG 2026 placeholder). "
        "Envelope Relay com cursor pagination. Publico — sem PII envolvida. "
        "Cada node inclui tipo, valor_base (BRL) e flag gratuito."
    ),
    response_model=EmolumentoTabelaV2Response,
    response_description="Tabela de emolumentos paginada.",
)
async def listar_tabela_emolumento_v2(
    _api_key: Annotated[str, Depends(require_cartorio_api_key)],
    first: int = Query(default=20, ge=1, le=100, description="Max itens por pagina (1-100)."),
    after: str | None = Query(default=None, description="Cursor opaque."),
    only_gratuitos: bool = Query(default=False, description="Filtrar apenas emolumentos gratuitos."),
) -> dict[str, Any]:
    """Lista tabela de emolumento com cursor pagination.

    Ordenacao: por tipo ASC (alfabetico, estavel para cursor).
    """
    from app.services.cursor import decode_cursor_safe

    # Sort por tipo para cursor estavel
    items = sorted(EMOLUMENTOS_2026.items(), key=lambda kv: kv[0])

    # Filtro
    if only_gratuitos:
        items = [(k, v) for k, v in items if v == Decimal("0.00")]

    # Cursor pagination (chave = tipo, nao id)
    if after:
        tipo_after = decode_cursor_safe(after, "tipo_after")
        if tipo_after is not None:
            items = [(k, v) for k, v in items if k > tipo_after]

    # Pega first+1 para detectar next page
    has_next_page = len(items) > first
    items = items[:first]

    edges = [
        Edge(
            cursor=encode_cursor({"tipo_after": tipo}),
            node=EmolumentoV2Node(
                tipo=tipo,
                valor_base=valor,
                gratuito=valor == Decimal("0.00"),
            ),
        )
        for tipo, valor in items
    ]

    end_cursor = edges[-1].cursor if edges and has_next_page else None

    return EmolumentoTabelaV2Response(
        edges=edges,
        page_info=PageInfo(has_next_page=has_next_page, end_cursor=end_cursor),
        total_count=len(items) if not after else len(EMOLUMENTOS_2026),  # paginado vs total
        tabela_referencia="TABELA_2026_MG",
        valido_ate="2026-12-31",
    ).model_dump(mode="json")