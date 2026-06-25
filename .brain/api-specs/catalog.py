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
    ApiEndpoint("POST", "/api/v1/cliente", "v1", "clientes", "Cria cliente", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/cliente/{id}", "v1", "clientes", "Busca cliente por ID", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/cliente/{id}/historico", "v1", "clientes", "Historico LGPD art. 18 IV", True, True, "stable"),
    ApiEndpoint("PATCH", "/api/v1/cliente/{id}", "v1", "clientes", "Corrige dados LGPD art. 18 III", True, True, "stable"),
    ApiEndpoint("DELETE", "/api/v1/cliente/{id}", "v1", "clientes", "Encerra cliente (cascade)", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/cliente/{id}/lgpd/portabilidade", "v1", "clientes", "Solicita portabilidade LGPD V", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/cliente/{id}/lgpd/portabilidade/download", "v1", "clientes", "Download portabilidade", True, True, "stable"),
    # --- Protocolos (6) ---
    ApiEndpoint("POST", "/api/v1/protocolo", "v1", "protocolos", "Cria protocolo", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/protocolo/{id}", "v1", "protocolos", "Busca protocolo por ID", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/protocolo", "v1", "protocolos", "Lista protocolos", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/protocolo/{id}/documento", "v1", "protocolos", "Anexa documento", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/protocolo/{id}/concluir", "v1", "protocolos", "Conclui protocolo", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/protocolo/{id}/cancelar", "v1", "protocolos", "Cancela protocolo", True, True, "stable"),
    # --- Emolumento (3) ---
    ApiEndpoint("POST", "/api/v1/emolumento/calcular", "v1", "emolumento", "Calcula emolumento", False, False, "stable"),
    ApiEndpoint("GET", "/api/v1/emolumento/tabela", "v1", "emolumento", "Lista tabela vigente", False, False, "stable"),
    ApiEndpoint("GET", "/api/v1/emolumento/{id}", "v1", "emolumento", "Busca emolumento por ID", False, False, "stable"),
    # --- Agendamento (5) ---
    ApiEndpoint("POST", "/api/v1/agendamento", "v1", "agendamento", "Cria agendamento", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/agendamento/{id}", "v1", "agendamento", "Busca agendamento", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/agendamento", "v1", "agendamento", "Lista agendamentos", True, True, "stable"),
    ApiEndpoint("PUT", "/api/v1/agendamento/{id}", "v1", "agendamento", "Atualiza agendamento", True, True, "stable"),
    ApiEndpoint("DELETE", "/api/v1/agendamento/{id}", "v1", "agendamento", "Cancela agendamento", True, True, "stable"),
    # --- LGPD direitos (6) ---
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/anonimizar", "v1", "lgpd", "LGPD anonimizacao", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/corrigir", "v1", "lgpd", "LGPD correcao", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/oposicao", "v1", "lgpd", "LGPD oposicao", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/optout", "v1", "lgpd", "LGPD opt-out marketing", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/portabilidade", "v1", "lgpd", "LGPD portabilidade", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/cliente/{id}/lgpd/esquecimento", "v1", "lgpd", "LGPD esquecimento (revoga consentimento)", True, True, "stable"),
    # --- Admin / Health (8) ---
    ApiEndpoint("GET", "/health", "v1", "admin", "Health basico", False, False, "stable"),
    ApiEndpoint("GET", "/health/radar", "v1", "admin", "Health 7 servicos", False, False, "stable"),
    ApiEndpoint("GET", "/health/db", "v1", "admin", "Health DB", False, False, "stable"),
    ApiEndpoint("GET", "/health/redis", "v1", "admin", "Health Redis", False, False, "stable"),
    ApiEndpoint("GET", "/health/llm", "v1", "admin", "Health LLM provider", False, False, "stable"),
    ApiEndpoint("GET", "/admin/audit/health", "v1", "admin", "Audit log dead man's switch", True, False, "stable"),
    ApiEndpoint("POST", "/admin/audit/check-now", "v1", "admin", "Trigger manual dead man's switch", True, False, "stable"),
    ApiEndpoint("GET", "/admin/locks", "v1", "admin", "Lista redlocks ativos", True, False, "stable"),
    # --- Admin / Pool + Slow queries + Retencao (5) ---
    ApiEndpoint("GET", "/admin/pool", "v1", "admin", "DB pool stats", True, False, "stable"),
    ApiEndpoint("GET", "/admin/slow-queries", "v1", "admin", "Slow queries (>200ms)", True, False, "stable"),
    ApiEndpoint("POST", "/admin/retencao/run", "v1", "admin", "Trigger retencao job", True, False, "stable"),
    ApiEndpoint("GET", "/admin/n8n/validate-wfs", "v1", "admin", "Valida WFs N8N (B12)", True, False, "stable"),
    ApiEndpoint("GET", "/admin/backup/status", "v1", "admin", "Status ultimo backup DB", True, False, "stable"),
    # --- Metrics + observability (3) ---
    ApiEndpoint("GET", "/api/v1/metrics/prometheus", "v1", "observability", "Prometheus metrics", False, False, "stable"),
    ApiEndpoint("GET", "/api/v1/metrics/n8n", "v1", "observability", "N8N metrics", True, False, "stable"),
    ApiEndpoint("GET", "/version", "v1", "observability", "Versao da API + links", False, False, "stable"),
    # --- Integrations (5) ---
    ApiEndpoint("POST", "/api/v1/integrations/opencode/test", "v1", "integrations", "Testa OpenCode-Go provider", True, False, "stable"),
    ApiEndpoint("POST", "/api/v1/integrations/openclaw/test", "v1", "integrations", "Testa OpenClaw gateway", True, False, "stable"),
    ApiEndpoint("POST", "/api/v1/integrations/n8n/error", "v1", "integrations", "Webhook N8N error handler (B06)", True, False, "stable"),
    ApiEndpoint("POST", "/api/v1/integrations/chatwoot/handoff", "v1", "integrations", "Handoff Chatwoot", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/integrations/status", "v1", "integrations", "Status todas integracoes", True, False, "stable"),
    # --- Atendimento (4) ---
    ApiEndpoint("POST", "/api/v1/atendimento", "v1", "atendimento", "Cria atendimento", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/atendimento/{id}", "v1", "atendimento", "Busca atendimento", True, True, "stable"),
    ApiEndpoint("GET", "/api/v1/atendimento", "v1", "atendimento", "Lista atendimentos", True, True, "stable"),
    ApiEndpoint("POST", "/api/v1/atendimento/{id}/finalizar", "v1", "atendimento", "Finaliza atendimento", True, True, "stable"),
    # --- Webhooks (2) ---
    ApiEndpoint("POST", "/api/v1/webhooks/evo-in", "v1", "webhooks", "Webhook Evolution API inbound", False, False, "stable"),
    ApiEndpoint("POST", "/api/v1/webhooks/chatwoot", "v1", "webhooks", "Webhook Chatwoot", False, False, "stable"),
)


# ============================================================================
# API v2 — ALPHA (4 endpoints)
# ============================================================================

API_V2_ENDPOINTS: tuple[ApiEndpoint, ...] = (
    ApiEndpoint("GET", "/api/v2/info", "v2", "meta", "API v2 metadata + sunset", False, False, "alpha"),
    ApiEndpoint("GET", "/api/v2/clientes", "v2", "clientes", "Lista clientes cursor Relay", True, True, "alpha"),
    ApiEndpoint("GET", "/api/v2/protocolos", "v2", "protocolos", "Lista protocolos cursor Relay", True, True, "alpha"),
    ApiEndpoint("GET", "/api/v2/emolumento/tabela", "v2", "emolumento", "Tabela emolumento cursor Relay", True, False, "alpha"),
)


def get_all_endpoints() -> tuple[ApiEndpoint, ...]:
    """Retorna TODOS endpoints v1 + v2."""
    return API_ENDPOINTS + API_V2_ENDPOINTS


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
    """Estatisticas agregadas do catalogo."""
    all_eps = get_all_endpoints()
    return {
        "total": len(all_eps),
        "v1": len(get_endpoints_by_version("v1")),
        "v2": len(get_endpoints_by_version("v2")),
        "lgpd_scope": len(get_endpoints_with_lgpd_scope()),
        "auth_required": sum(1 for e in all_eps if e.auth_required),
        "alpha": sum(1 for e in all_eps if e.status == "alpha"),
        "stable": sum(1 for e in all_eps if e.status == "stable"),
    }