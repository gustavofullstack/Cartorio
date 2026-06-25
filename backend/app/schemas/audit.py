"""Schemas Pydantic v2 do recurso AuditLog.

Cobre:
- AuditLogCreate: payload de entrada de POST /api/v1/audit/log (D0.2 2026-06-25)
- AuditLogCreatedResponse: resposta 201 com id/hash/prev_hash/created_at
- AuditLogResponse: saida paginada de GET /api/v1/audit/logs (DPO/escrevente)
- AuditLogListResponse: envelope com items + pagination metadata
- AuditLogFilter: query params para filtrar por actor/action/resource/periodo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Input (D0.2 — POST /api/v1/audit/log)
# ============================================================================


class AuditLogCreate(BaseModel):
    """Payload de entrada para POST /api/v1/audit/log.

    LGPD art. 37 — registro de tratamento. Consumidores:
    - WF 23 LGPD Esqueci (revogacao de consentimento)
    - N8N jobs que precisam gravar acoes sem depender de ORM direto

    Campos:
    - actor_id: QUEM executou. Default 'system' para chamadas internas de n8n/cron.
        Pattern: ^[a-zA-Z0-9_.-]{1,64}$ — rejeita CPF, email, espacos, chars
        especiais. Bloqueia tentativa de incluir dado pessoal em campo que
        deveria ser apenas identificador.
    - action: O QUE (ex: 'cliente.revogacao.consentimento', 'protocolo.update').
    - resource: ALVO (ex: 'cliente:42', 'protocolo:2026-00001').
    - payload: estado serializado (before/after quando aplicavel).
        AVISO LGPD (D0.2 P1.1): caller DEVE pre-scrub PII. Endpoint detecta
        via pii.detect_only() e emite warning no response — NAO bloqueia.
    - canal: origem (whatsapp, telegram, web, balcao, email, n8n, cron, system).
    - ip, user_agent, request_id: contexto de request (opcional).
        NOTA (D0.2 P0.1): campo `ip` eh ACEITO no schema (backward compat)
        mas o HANDLER SEMPRE sobrescreve com request.client.host (honra XFF).
        Caller NAO confia no proprio `ip` — usar o que o servidor gravou.
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(
        default="system",
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_.-]{1,64}$",
        description=(
            "Quem executou a acao. Default 'system' para chamadas internas. "
            "Pattern: ^[a-zA-Z0-9_.-]{1,64}$ — rejeita CPF, email, espacos. "
            "Bloqueia tentativa de incluir dado pessoal em campo identificador."
        ),
    )
    actor_type: Literal["user", "system", "bot", "escrevente", "tabeliao"] = Field(
        default="system",
        description="Tipo de ator (LGPD-by-design, default 'system' para n8n/cron).",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Acao executada (ex: 'cliente.revogacao.consentimento').",
    )
    resource: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Recurso afetado (ex: 'cliente:42', 'protocolo:2026-00001').",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Estado serializado (before/after quando aplicavel). "
            "LGPD D0.2 P1.1: payload DEVE ser pre-scrubbed pelo caller. "
            "PII (CPF, email, telefone) NAO deve ser incluida. Endpoint "
            "emite warning no response (campo pii_warning) se detectar PII "
            "via pii.detect_only() — NAO bloqueia, apenas sinaliza. "
            "Scrub automatico: Sprint 4 (P2 backlog)."
        ),
    )
    canal: (
        Literal["whatsapp", "telegram", "web", "balcao", "email", "n8n", "cron", "system"] | None
    ) = Field(
        default=None,
        description="Canal de origem. None para chamadas externas sem canal definido.",
    )
    ip: str | None = Field(
        default=None,
        max_length=45,
        description=(
            "IP COMPLETO do cliente. LGPD D5 — truncado automaticamente em /24 ou /32. "
            "D0.2 P0.1: handler SEMPRE sobrescreve com request.client.host "
            "(honra XFF). Campo mantido para backward compat mas NAO confiavel."
        ),
    )
    user_agent: str | None = Field(
        default=None,
        max_length=512,
        description="User-Agent do request.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=64,
        description="ID unico do request (UUIDv4) para correlacao.",
    )


class PIIWarning(BaseModel):
    """Aviso de PII detectado no payload (D0.2 P1.1).

    NAO bloqueia o request — apenas sinaliza ao caller que o payload
    continha dados que PODEM ser pessoais. Caller pode decidir reagendar
    com payload pre-scrubbed.

    Sprint 4 (P2 backlog): implementar scrub automatico antes de gravar.
    """

    model_config = ConfigDict(from_attributes=True)

    detected: bool = Field(..., description="True se pii.detect_only() encontrou matches.")
    fields: list[str] = Field(
        ...,
        description=(
            "Lista de tipos de PII detectados (ex: ['cpf', 'email']). Vazio se detected=False."
        ),
    )


class AuditLogCreatedResponse(BaseModel):
    """Resposta 201 de POST /api/v1/audit/log.

    Retorna apenas os campos essenciais para o caller confirmar a chain:
    - id: ID sequencial da entrada criada
    - hash: hash SHA256 desta entry (chain integrity)
    - prev_hash: hash da entry anterior (None se for a primeira)
    - created_at: timestamp UTC do registro
    - pii_warning: aviso de PII detectado no payload (D0.2 P1.1). None se
        payload nao continha PII.

    Caller NAO precisa do payload/IP/etc — para isso existe GET /audit/logs/{id}.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID sequencial da entrada criada.")
    hash: str = Field(..., description="Hash SHA256 desta entry (chain integrity).")
    prev_hash: str | None = Field(
        default=None, description="Hash da entry anterior (None se for a primeira)."
    )
    created_at: datetime = Field(..., description="Timestamp UTC do registro.")
    pii_warning: PIIWarning | None = Field(
        default=None,
        description=(
            "Aviso de PII detectado no payload via pii.detect_only(). "
            "None se payload nao continha PII. NAO bloqueia — apenas sinaliza."
        ),
    )


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
    resource: str = Field(
        ..., description="Recurso afetado (ex: cliente:42, protocolo:2026-00001)."
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Estado serializado (before/after quando aplicavel).",
    )
    ip: str | None = Field(
        default=None,
        description=(
            "IP COMPLETO do cliente (com XFF, primeiro hop). "
            "DADO PESSOAL (LGPD art. 5 II). Acesso restrito via role-gate 'dpo'. "
            "Para tier != 'dpo', campo vem como null e usar ip_truncated."
        ),
    )
    ip_truncated: str | None = Field(
        default=None,
        description=(
            "IP truncado em /24 (IPv4) ou /32 (IPv6). LGPD D5. "
            "Para logs de aplicacao, /metrics, e queries normais. "
            "Preserva subnet para forensics sem expor host."
        ),
    )
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


__all__ = [
    "AuditLogCreate",
    "AuditLogCreatedResponse",
    "AuditLogFilter",
    "AuditLogListResponse",
    "AuditLogResponse",
    "PIIWarning",
]
