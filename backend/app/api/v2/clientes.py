"""GET /api/v2/clientes — listagem com cursor pagination Relay-style (A24.2).

API v2 quebra de v1:
- offset/limit v1 -> cursor (opaco base64) v2
- Envelope flat v1 -> envelope Relay v2 (edges + page_info + nodes)

LGPD art. 37: response NAO expoe CPF puro (apenas cpf_hash).
Clientes encerrados (motivo_encerramento != null) sao excluidos por default.

Auth: X-API-Key (mesma v1). JWT sera adicionado em A24.x como alternativa.

Referencia: docs/api-v1-to-v2-migration.md (A24.6).
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.db import get_db
from app.models.cliente import Cliente

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clientes", tags=["v2", "clientes"])


# ============================================================================
# Schemas (Pydantic v2)
# ============================================================================


class ClienteV2Node(BaseModel):
    """Node do cliente LGPD-safe."""

    id: int
    cpf_hash: str  # hash SHA256, NAO CPF puro (LGPD art. 37)
    nome: str
    email: str | None = None
    consentimento_lgpd: bool
    motivo_encerramento: str | None = None


class Edge(BaseModel):
    cursor: str
    node: ClienteV2Node


class PageInfo(BaseModel):
    has_next_page: bool
    end_cursor: str | None = None


class ClientesV2Response(BaseModel):
    edges: list[Edge]
    page_info: PageInfo
    total_count: int


# ============================================================================
# Cursor helpers
# ============================================================================


def _encode_cursor(id_after: int) -> str:
    """Codifica cursor opaque base64 (Relay-style)."""
    payload = json.dumps({"id_after": id_after}).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    """Decodifica cursor opaque (usado em testes)."""
    padded = cursor + "=" * (-len(cursor) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


# ============================================================================
# Endpoint
# ============================================================================


@router.get(
    "",
    summary="Lista clientes (v2, cursor pagination)",
    description=(
        "Lista clientes do cartorio com paginacao Relay-style (edges + pageInfo). "
        "Clientes encerrados (LGPD art. 18 VI) sao excluidos por default. "
        "Use `include_encerrados=true` para incluir. "
        "Ordenacao estavel por id ASC garante cursor consistente."
    ),
    response_model=ClientesV2Response,
    response_description="Lista de clientes paginada.",
)
async def listar_clientes_v2(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)],
    first: int = Query(default=20, ge=1, le=100, description="Max itens por pagina (1-100)."),
    after: str | None = Query(default=None, description="Cursor opaque da pagina anterior."),
    include_encerrados: bool = Query(default=False, description="Incluir clientes com motivo_encerramento setado."),
) -> dict[str, Any]:
    """Lista clientes com cursor pagination (Relay-style)."""
    # Query base
    stmt = select(Cliente).order_by(Cliente.id.asc())

    # Filtro LGPD: excluir encerrados por default
    if not include_encerrados:
        stmt = stmt.where(Cliente.motivo_encerramento.is_(None))

    # Cursor pagination: WHERE id > {decoded.id_after}
    if after:
        try:
            decoded = _decode_cursor(after)
            id_after = int(decoded["id_after"])
            stmt = stmt.where(Cliente.id > id_after)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.warning("v2 clientes: cursor invalido '%s': %s", after, e)
            # Cursor invalido = retorna primeira pagina (fail-soft, nao 400)

    # Limita a first+1 para detectar has_next_page
    stmt = stmt.limit(first + 1)

    rows = list(db.execute(stmt).scalars().all())

    has_next_page = len(rows) > first
    rows = rows[:first]

    edges = [
        Edge(
            cursor=_encode_cursor(c.id),
            node=ClienteV2Node(
                id=c.id,
                cpf_hash=c.cpf_hash,
                nome=c.nome,
                email=c.email,
                consentimento_lgpd=c.consentimento_lgpd,
                motivo_encerramento=c.motivo_encerramento.value
                if c.motivo_encerramento is not None
                else None,
            ),
        )
        for c in rows
    ]

    # end_cursor eh None na ultima pagina (has_next_page=False)
    end_cursor = edges[-1].cursor if edges and has_next_page else None

    # Total count (sem filtro de cursor — total geral respeitando include_encerrados)
    from sqlalchemy import func

    total_stmt = select(func.count(Cliente.id))
    if not include_encerrados:
        total_stmt = total_stmt.where(Cliente.motivo_encerramento.is_(None))
    total_count = int(db.execute(total_stmt).scalar_one() or 0)

    return ClientesV2Response(
        edges=edges,
        page_info=PageInfo(has_next_page=has_next_page, end_cursor=end_cursor),
        total_count=total_count,
    ).model_dump()