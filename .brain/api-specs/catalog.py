"""API Endpoints Catalog — BRAIN2.

Catalogo estatico de TODOS os endpoints REST da API FastAPI v1 e v2.
Gerado a partir do OpenAPI spec + categorizacao manual.

Uso:
    from brain.api_specs.catalog import API_ENDPOINTS, get_endpoints_by_tag
    endpoints = get_endpoints_by_tag('clientes')
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiEndpoint:
    """Endpoint catalogado."""

    method: str  # GET, POST, PUT, PATCH, DELETE
    path: str  # /api/v1/clientes/{id}
    version: str  # "v1" | "v2"
    tag: str  # categoria
    summary: str  # descricao curta
    auth_required: bool  # X-API-Key ou JWT
    lgpd_scope: bool  # acessa PII?
    status: str  # stable | beta | alpha | deprecated


# ============================================================================
# API v1 — STABLE (50+ endpoints)
# ============================================================================

API_ENDPOINTS: tuple[ApiEndpoint, ...] = (
    # --- Clientes (8) ---
    ApiEndpoint(
        "POST",
        "/api/v1/cliente",
        "v1",
        "clientes",
        "Cria cliente",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/cliente/{id}",
        "v1",
        "clientes",
        "Busca cliente por ID",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/cliente/{id}/historico",
        "v1",
        "clientes",
        "Historico LGPD art. 18 IV",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "PATCH",
        "/api/v1/cliente/{id}",
        "v1",
        "clientes",
        "Corrige dados LGPD art. 18 III",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "DELETE",
        "/api/v1/cliente/{id}",
        "v1",
        "clientes",
        "Encerra cliente (cascade)",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/cliente/{id}/lgpd/portabilidade",
        "v1",
        "clientes",
        "Solicita portabilidade LGPD V",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/cliente/{id}/lgpd/portabilidade/download",
        "v1",
        "clientes",
        "Download portabilidade",
        True,
        True,
        "stable",
    ),
    # --- Protocolos (6) ---
    ApiEndpoint(
        "POST",
        "/api/v1/protocolo",
        "v1",
        "protocolos",
        "Cria protocolo",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/protocolo/{id}",
        "v1",
        "protocolos",
        "Busca protocolo por ID",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/protocolo",
        "v1",
        "protocolos",
        "Lista protocolos",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/protocolo/{id}/documento",
        "v1",
        "protocolos",
        "Anexa documento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/protocolo/{id}/concluir",
        "v1",
        "protocolos",
        "Conclui protocolo",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/protocolo/{id}/cancelar",
        "v1",
        "protocolos",
        "Cancela protocolo",
        True,
        True,
        "stable",
    ),
    # --- Emolumento (3) ---
    ApiEndpoint(
        "POST",
        "/api/v1/emolumento/calcular",
        "v1",
        "emolumento",
        "Calcula emolumento",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/emolumento/tabela",
        "v1",
        "emolumento",
        "Lista tabela vigente",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/emolumento/{id}",
        "v1",
        "emolumento",
        "Busca emolumento por ID",
        False,
        False,
        "stable",
    ),
    # --- Agendamento (5) ---
    ApiEndpoint(
        "POST",
        "/api/v1/agendamento",
        "v1",
        "agendamento",
        "Cria agendamento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/agendamento/{id}",
        "v1",
        "agendamento",
        "Busca agendamento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/agendamento",
        "v1",
        "agendamento",
        "Lista agendamentos",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "PUT",
        "/api/v1/agendamento/{id}",
        "v1",
        "agendamento",
        "Atualiza agendamento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "DELETE",
        "/api/v1/agendamento/{id}",
        "v1",
        "agendamento",
        "Cancela agendamento",
        True,
        True,
        "stable",
    ),
    # --- LGPD direitos (6) ---
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/anonimizar",
        "v1",
        "lgpd",
        "LGPD anonimizacao",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/corrigir",
        "v1",
        "lgpd",
        "LGPD correcao",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/oposicao",
        "v1",
        "lgpd",
        "LGPD oposicao",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/optout",
        "v1",
        "lgpd",
        "LGPD opt-out marketing",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/portabilidade",
        "v1",
        "lgpd",
        "LGPD portabilidade",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/cliente/{id}/lgpd/esquecimento",
        "v1",
        "lgpd",
        "LGPD esquecimento (revoga consentimento)",
        True,
        True,
        "stable",
    ),
    # --- Admin / Health (10) --- G7 Wave 15: paths canonicos /api/v1/*
    ApiEndpoint(
        "GET",
        "/health",
        "v1",
        "admin",
        "Health basico (root alias)",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/health/radar",
        "v1",
        "admin",
        "Health 7 servicos (db/redis/n8n/openclaw/evo/chatwoot/supabase)",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/health/radar/expanded",
        "v1",
        "admin",
        "Radar expandido DNS+Traefik+SSH+disk (G6/G7)",
        False,
        False,
        "beta",
    ),
    ApiEndpoint(
        "GET", "/api/v1/health/db", "v1", "admin", "Health DB", False, False, "stable"
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/health/redis",
        "v1",
        "admin",
        "Health Redis",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/health/llm",
        "v1",
        "admin",
        "Health LLM provider",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/health/backup",
        "v1",
        "admin",
        "Health ultimo backup",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/admin/audit/health",
        "v1",
        "admin",
        "Audit log dead man's switch",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/admin/audit/check-now",
        "v1",
        "admin",
        "Trigger manual dead man's switch",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/admin/locks",
        "v1",
        "admin",
        "Lista redlocks ativos",
        True,
        False,
        "stable",
    ),
    # --- Admin / Pool + Slow queries + Retencao (5) ---
    ApiEndpoint(
        "GET",
        "/api/v1/admin/pool",
        "v1",
        "admin",
        "DB pool stats",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/admin/slow-queries",
        "v1",
        "admin",
        "Slow queries (>200ms)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/admin/retencao/run",
        "v1",
        "admin",
        "Trigger retencao job",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/admin/n8n/validate-wfs",
        "v1",
        "admin",
        "Valida WFs N8N (B12)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/admin/backup/status",
        "v1",
        "admin",
        "Status ultimo backup DB",
        True,
        False,
        "stable",
    ),
    # --- Metrics + observability (3) ---
    ApiEndpoint(
        "GET",
        "/api/v1/metrics/prometheus",
        "v1",
        "observability",
        "Prometheus metrics",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/metrics/n8n",
        "v1",
        "observability",
        "N8N metrics",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/version",
        "v1",
        "observability",
        "Versao da API + links",
        False,
        False,
        "stable",
    ),
    # --- Integrations (5) ---
    ApiEndpoint(
        "POST",
        "/api/v1/integrations/opencode/test",
        "v1",
        "integrations",
        "Testa OpenCode-Go provider",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/integrations/openclaw/test",
        "v1",
        "integrations",
        "Testa OpenClaw gateway",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/integrations/n8n/error",
        "v1",
        "integrations",
        "Webhook N8N error handler (B06)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/integrations/chatwoot/handoff",
        "v1",
        "integrations",
        "Handoff Chatwoot",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/integrations/status",
        "v1",
        "integrations",
        "Status todas integracoes",
        True,
        False,
        "stable",
    ),
    # --- Atendimento (4) ---
    ApiEndpoint(
        "POST",
        "/api/v1/atendimento",
        "v1",
        "atendimento",
        "Cria atendimento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/atendimento/{id}",
        "v1",
        "atendimento",
        "Busca atendimento",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/atendimento",
        "v1",
        "atendimento",
        "Lista atendimentos",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/atendimento/{id}/finalizar",
        "v1",
        "atendimento",
        "Finaliza atendimento",
        True,
        True,
        "stable",
    ),
    # --- Webhooks (4) ---
    ApiEndpoint(
        "POST",
        "/api/v1/webhooks/evo-in",
        "v1",
        "webhooks",
        "Webhook Evolution API inbound",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/webhook/evolution",
        "v1",
        "webhooks",
        "Webhook Evolution dual-format (legacy path)",
        False,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/webhook/evolution/health",
        "v1",
        "webhooks",
        "Health ingest Evolution",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/webhooks/chatwoot",
        "v1",
        "webhooks",
        "Webhook Chatwoot",
        False,
        False,
        "stable",
    ),
    # --- WebSocket (1) ---
    ApiEndpoint(
        "WS",
        "/api/v1/ws/atendimentos",
        "v1",
        "websocket",
        "WS atendimentos tempo real (ping/pong)",
        True,
        True,
        "stable",
    ),
    # --- BRAIN meta (6) ---
    ApiEndpoint(
        "GET",
        "/api/v1/brain/tasks",
        "v1",
        "brain",
        "Lista tasks harness/brain",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/brain/lessons",
        "v1",
        "brain",
        "Lista lessons MEMORY",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/brain/lessons",
        "v1",
        "brain",
        "Cria lesson",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/brain/sync",
        "v1",
        "brain",
        "Trigger sync brain",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/brain/loop-state",
        "v1",
        "brain",
        "Estado do loop engineer",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/brain/context",
        "v1",
        "brain",
        "Contexto atual snapshot",
        True,
        False,
        "stable",
    ),
    # --- Telegram bot (6) --- F4 [P1] RETRY 2026-07-15 / Lesson 178
    # Source: backend/app/api/v1/telegram.py (router prefix /telegram, tags=["telegram"])
    # Auth: webhook usa X-Telegram-Bot-Api-Secret-Token (HMAC compare_digest, timing-safe).
    #       health/metrics sao publicos. set-commands precisa de X-API-Key.
    ApiEndpoint(
        "POST",
        "/api/v1/telegram/webhook",
        "v1",
        "telegram-webhook",
        "Telegram bot webhook handler (PII scrub 3 camadas + debounce + idempotency Redis SETNX)",
        False,
        True,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/telegram/health",
        "v1",
        "telegram-health",
        "Telegram bot health check (200 ok)",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/telegram/metrics",
        "v1",
        "telegram-metrics",
        "Telegram bot metrics Prometheus (counter/histogram)",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/telegram/debug/last-updates",
        "v1",
        "telegram-debug",
        "Debug buffer ultimas updates (apenas se TELEGRAM_DEBUG_MODE=true)",
        True,
        True,
        "beta",
    ),
    ApiEndpoint(
        "GET",
        "/api/v1/telegram/webhook/info",
        "v1",
        "telegram-webhook-info",
        "Info do webhook configurado (url + pending + last_error)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/telegram/set-commands",
        "v1",
        "telegram-admin",
        "Registra command list do bot via BotFather API (X-API-Key required)",
        True,
        False,
        "alpha",
    ),
)


# ============================================================================
# API v2 — ALPHA (4 endpoints)
# ============================================================================

API_V2_ENDPOINTS: tuple[ApiEndpoint, ...] = (
    ApiEndpoint(
        "GET",
        "/api/v2/info",
        "v2",
        "meta",
        "API v2 metadata + sunset",
        False,
        False,
        "alpha",
    ),
    ApiEndpoint(
        "GET",
        "/api/v2/clientes",
        "v2",
        "clientes",
        "Lista clientes cursor Relay",
        True,
        True,
        "alpha",
    ),
    ApiEndpoint(
        "GET",
        "/api/v2/protocolos",
        "v2",
        "protocolos",
        "Lista protocolos cursor Relay",
        True,
        True,
        "alpha",
    ),
    ApiEndpoint(
        "GET",
        "/api/v2/emolumento/tabela",
        "v2",
        "emolumento",
        "Tabela emolumento cursor Relay",
        True,
        False,
        "alpha",
    ),
)


# ============================================================================
# OpenClaw Gateway — WS + OpenAI-compatible REST (Squad E / E8)
# ============================================================================
# Endpoint externo gerenciado por `cartorio_openclaw-gateway` no Swarm
# (host `agent.2notasudi.com.br`, porta interna 18789 + TLS Traefik 443).
# Protocolo proprio (WS) + camada REST OpenAI-compat.
# Auth: `gateway.auth.token` (env `OPENCLAW_GATEWAY_TOKEN`) + opcional
# `gateway.auth.password` (env `OPENCLAW_GATEWAY_PASSWORD`). Scope
# `operator.read|operator.write|operator.admin` exigido para metodos nao-health.
#
# Validado 2026-07-15 (lesson-177-openclaw-e8-finalize-2026-07-14):
#   - GET /health                              -> 200 JSON {"ok":true,...}
#   - GET /v1/models                           -> 401 sem auth; 200 com token
#   - POST /v1/chat/completions                -> 401 sem auth; OpenAI-compat
#   - WS  wss://.../v1/chat                    -> handshake connect.challenge
#     -> connect req(method=connect, params={auth.token, role=operator})
#     -> hello-ok {protocol:4, server:2026.7.1, 218 methods, 30 events}
#
# Frame shapes:
#   req:  {type:"req", id, method, params}
#   res:  {type:"res", id, ok, payload|error}
#   event:{type:"event", event, payload, seq?, stateVersion?}
#
# Metodos relevantes (subset, ver features.methods em hello-ok):
#   agents.list / agents.create / agents.update / agents.delete
#   models.list / models.authStatus
#   skills.status / skills.search / skills.install / skills.update
#   tools.catalog / tools.invoke
#   config.get / config.set / config.apply / config.schema
#   sessions.send / sessions.list / sessions.subscribe
#   status / health / diagnostics.stability / logs.tail
#   node.pair.request / node.pair.approve
#   device.pair.list / device.pair.approve
#   channels.status / channels.start / channels.stop
#
# Gaps E8 conhecidos:
#   - defaultAgentId="main" (agent padrao). `cartorio-bot` NAO existe.
#   - hello-ok.auth.scopes=[] para o token atual (health-only). Bloqueia
#     agents.list / agents.create ate Gustavo ajustar openclaw.json ou
#     gerar operator token com scopes no gateway.

OPENCLAW_GATEWAY_BASE = "https://agent.2notasudi.com.br"
OPENCLAW_GATEWAY_WS = "wss://agent.2notasudi.com.br/v1/chat"

OPENCLAW_GATEWAY_ENDPOINTS: tuple[ApiEndpoint, ...] = (
    ApiEndpoint(
        "GET",
        "/health",
        "oc",
        "openclaw-health",
        "Health snapshot (event loop + plugins + model pricing)",
        False,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/v1/models",
        "oc",
        "openclaw-models",
        "Lista modelos agent-first (openclaw, openclaw/<agentId>)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "GET",
        "/v1/models/{id}",
        "oc",
        "openclaw-models",
        "Detalhe de um modelo",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/v1/chat/completions",
        "oc",
        "openclaw-chat",
        "Chat completions (formato OpenAI-compatible)",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/v1/responses",
        "oc",
        "openclaw-chat",
        "Agent-native responses endpoint",
        True,
        True,
        "beta",
    ),
    ApiEndpoint(
        "POST",
        "/v1/embeddings",
        "oc",
        "openclaw-models",
        "Embeddings (RAG pipelines)",
        True,
        False,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/tools/invoke",
        "oc",
        "openclaw-tools",
        "Invoca tool registrada no gateway",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "WS",
        "/v1/chat",
        "oc",
        "openclaw-ws",
        "Gateway WS protocol v4 (connect/hello-ok + 218 methods + 30 events)",
        True,
        True,
        "stable",
    ),
    ApiEndpoint(
        "POST",
        "/api/v1/admin/rpc",
        "oc",
        "openclaw-admin",
        "Admin HTTP RPC (plugin default-off)",
        True,
        False,
        "alpha",
    ),
)


def get_all_endpoints() -> tuple[ApiEndpoint, ...]:
    """Retorna TODOS endpoints v1 + v2 + openclaw gateway."""
    return API_ENDPOINTS + API_V2_ENDPOINTS + OPENCLAW_GATEWAY_ENDPOINTS


def get_endpoints_by_tag(tag: str) -> tuple[ApiEndpoint, ...]:
    """Filtra endpoints por tag (categoria)."""
    return tuple(e for e in get_all_endpoints() if e.tag == tag)


def get_endpoints_by_version(version: str) -> tuple[ApiEndpoint, ...]:
    """Filtra endpoints por versao (v1/v2)."""
    return tuple(e for e in get_all_endpoints() if e.version == version)


def get_endpoints_with_lgpd_scope() -> tuple[ApiEndpoint, ...]:
    """Endpoints que acessam PII (LGPD scope)."""
    return tuple(e for e in get_all_endpoints() if e.lgpd_scope)


def get_stats() -> dict[str, int]:
    """Estatisticas agregadas do catalogo (v1 + v2 + openclaw)."""
    all_eps = get_all_endpoints()
    by_status: dict[str, int] = {}
    for e in all_eps:
        by_status[e.status] = by_status.get(e.status, 0) + 1
    return {
        "total": len(all_eps),
        "v1": len(get_endpoints_by_version("v1")),
        "v2": len(get_endpoints_by_version("v2")),
        "openclaw": len(get_endpoints_by_version("oc")),
        "lgpd_scope": len(get_endpoints_with_lgpd_scope()),
        "auth_required": sum(1 for e in all_eps if e.auth_required),
        "alpha": by_status.get("alpha", 0),
        "beta": by_status.get("beta", 0),
        "stable": by_status.get("stable", 0),
        "deprecated": by_status.get("deprecated", 0),
        "websocket": sum(1 for e in all_eps if e.method == "WS"),
    }
