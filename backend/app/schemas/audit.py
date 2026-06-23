"""Schemas Pydantic v2 do recurso AuditLog.

Cobre:
- AuditLogResponse: saida paginada de GET /api/v1/audit/logs (DPO/escrevente)
- AuditLogListResponse: envelope com items + pagination metadata
- AuditLogFilter: query params para filtrar por actor/action/resource/periodo
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Response
# ============================================================================


class AuditLogResponse(BaseModel):
    """Entrada de audit log (LGPD art. 37 - registro de tratamento)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID sequencial da entrada.")
    actor_id: str = Field(..., description="Quem executou a acao (escrevente, bot, system, ...).")
    actor_type: str = Field(..., description="Tipo: user, system, bot, escrevente, tabeliao.")
    action: str = Field(..., description="Acao executada (ex: cliente.delete.soft).")
    resource: str = Field(..., description="Recurso afetado (ex: cliente:42, protocolo:2026-00001).")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Estado serializado (before/after quando aplicavel).",
    )
    ip: str | None = Field(default=None, description="IP do cliente (com XFF, primeiro hop).")
    user_agent: str | None = Field(default=None, description="User-Agent do request.")
    request_id: str | None = Field(default=None, description="ID unico do request (UUIDv4).")
    canal: str | None = Field(
        default=None,
        description="Canal de origem (whatsapp, telegram, web, balcao, email, n8n, cron, system).",
    )
    timestamp: datetime = Field(..., description="Quando a acao foi registrada (UTC).")
    prev_hash: str | None = Field(default=None, description="Hash da entry anterior (chain).")
    hash: str = Field(..., description="Hash SHA256 desta entry (chain integrity).")


class AuditLogListResponse(BaseModel):
    """Envelope de listagem paginada."""

    items: list[AuditLogResponse] = Field(..., description="Items da pagina atual.")
    total: int = Field(..., description="Total de items que match o filtro (sem paginacao).")
    page: int = Field(..., description="Pagina atual (1-indexed).")
    page_size: int = Field(..., description="Tamanho da pagina (default 50, max 200).")
    has_next: bool = Field(..., description="Se ha proxima pagina.")


# ============================================================================
# Filtros
# ============================================================================


class AuditLogFilter(BaseModel):
    """Filtros de busca no audit log. Todos sao opcionais e AND entre si."""

    actor_id: str | None = Field(default=None, description="Filtrar por actor_id exato.")
    actor_type: Literal["user", "system", "bot", "escrevente", "tabeliao"] | None = Field(
        default=None, description="Filtrar por tipo de ator."
    )
    action_prefix: str | None = Field(
        default=None,
        description="Filtrar por prefixo de action (ex: 'cliente.delete' match 'cliente.delete.hard' e 'cliente.delete.soft').",
    )
    resource: str | None = Field(default=None, description="Filtrar por resource exato.")
    canal: str | None = Field(default=None, description="Filtrar por canal.")
    since: datetime | None = Field(default=None, description="Entries >= since.")
    until: datetime | None = Field(default=None, description="Entries <= until.")
    page: int = Field(default=1, ge=1, description="Pagina (1-indexed).")
    page_size: int = Field(default=50, ge=1, le=200, description="Tamanho da pagina.")


__all__ = ["AuditLogFilter", "AuditLogListResponse", "AuditLogResponse"]
