"""OpenAPI enhancer middleware (F6 [P2] 2026-07-15).

Customiza o schema OpenAPI gerado pelo FastAPI para melhorar a experiencia
do Swagger UI e ReDoc sem mexer em `paths` (apenas metadata):

- Adiciona `info.contact` canonico (Cartorio 2o Notas + DPO email).
- Adiciona `info.license` (LGPL-3.0).
- Adiciona `tags` ordenados com descricoes canonicas para o agrupamento
  no Swagger UI (Health, Telegram, LGPD, Audit, Brain, OpenClaw, Auth).
- Adiciona `servers` (production + dev local).
- Adiciona `components.securitySchemes` explicito (X-API-Key + Bearer JWT).

Instalacao via hook `app.openapi = custom_openapi` no main.py.

Nao altera NENHUM path existente. Apenas enrich o envelope OpenAPI.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

API_CONTACT = {
    "name": "Cartorio 2o Notas Uberlandia",
    "url": "https://2notasudi.com.br",
    "email": "suporte@2notasudi.com.br",
}

API_LICENSE = {
    "name": "LGPL-3.0",
    "url": "https://www.gnu.org/licenses/lgpl-3.0.html",
}

API_SERVERS = [
    {
        "url": "https://api.2notasudi.com.br",
        "description": "Production (EasyPanel + Traefik)",
    },
    {
        "url": "http://localhost:8000",
        "description": "Local dev (uvicorn --reload)",
    },
    {
        "url": "http://localhost:8000",
        "description": "Staging VPS Hostinger (100.99.172.84)",
    },
]

API_TAGS_ORDERED = [
    {
        "name": "Health",
        "description": (
            "Health checks (liveness, readiness, radar multi-servico + "
            "radar expanded com DNS/Traefik/SSH/Tailscale/Disk)."
        ),
    },
    {
        "name": "Telegram",
        "description": (
            "Telegram bot webhook + health/metrics/debug. "
            "Auth via header X-Telegram-Bot-Api-Secret-Token (HMAC)."
        ),
    },
    {
        "name": "WhatsApp",
        "description": (
            "WhatsApp Evolution API inbound + health/metrics/test send. "
            "Suporta ambos formatos legacy + aninhado."
        ),
    },
    {
        "name": "LGPD",
        "description": (
            "LGPD Art. 18 direitos do titular (anonimizar, corrigir, oposicao, "
            "optout, portabilidade, esquecimento) + DPO dashboard (JWT)."
        ),
    },
    {
        "name": "Audit",
        "description": (
            "Integridade do audit log (SHA256 chain + HMAC). "
            "Dead man's switch 3-level + 4-level + check-now manual."
        ),
    },
    {
        "name": "Brain",
        "description": (
            "BRAIN2 tasks/lessons/sync/loop-state/context. "
            "API publica para tooling de squads (cartorio-*)."
        ),
    },
    {
        "name": "OpenClaw",
        "description": (
            "OpenClaw gateway (REST OpenAI-compat + WS v4 + Admin RPC). "
            "Bearer token via env OPENCLAW_GATEWAY_TOKEN."
        ),
    },
    {
        "name": "Auth",
        "description": (
            "Auth login/refresh (JWT para DPO/operador). Sprint 4+: substituir por Supabase Auth."
        ),
    },
    {
        "name": "Cliente",
        "description": "CRUD cliente (LGPD-by-design: CPF/Telefone hashed).",
    },
    {
        "name": "Protocolo",
        "description": (
            "Ciclo de vida do protocolo (DRAFT -> EM_ANDAMENTO -> CONCLUIDO). HITL obrigatorio."
        ),
    },
    {
        "name": "Emolumento",
        "description": "Calculo de emolumentos (TABELA_2026_MG). Publico.",
    },
    {
        "name": "Atendimento",
        "description": "Handoff humano + pesquisa de satisfacao.",
    },
    {
        "name": "Integrations",
        "description": (
            "Integracoes externas (OpenCode-Go, OpenClaw, N8N, Chatwoot). X-API-Key required."
        ),
    },
    {
        "name": "Webhooks",
        "description": "Webhooks inbound (Evolution, Chatwoot).",
    },
    {
        "name": "Observability",
        "description": "Prometheus metrics + N8N metrics.",
    },
    {
        "name": "Admin",
        "description": (
            "Endpoints administrativos (X-API-Key required): "
            "pool, slow-queries, retencao, locks, n8n-validate."
        ),
    },
    {
        "name": "Meta",
        "description": "Discovery (health, MCP servers, version).",
    },
    {
        "name": "Dev",
        "description": "Ferramentas de desenvolvimento (Postman collection, etc).",
    },
]

SECURITY_SCHEMES = {
    "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": (
            "X-API-Key canonico para endpoints admin/integrations. "
            "Env: CARTORIO_API_KEY (DPO/admin), N8N_API_KEY (workflow N8N). "
            "3-tier rate limit: N8N 600/min, DPO 60/min, default 30/min."
        ),
    },
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": (
            "JWT para endpoints LGPD v2 / DPO dashboard. Mint via POST /api/v1/auth/login."
        ),
    },
    "TelegramWebhookSecret": {
        "type": "apiKey",
        "in": "header",
        "name": "X-Telegram-Bot-Api-Secret-Token",
        "description": ("Telegram webhook HMAC secret. Compare_digest (timing-safe)."),
    },
}


def _merge_tags(unique_existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mescla tag metadata canonica (ordem preservada) com tags ja existentes.

    Tags novas (presentes em API_TAGS_ORDERED mas nao no schema) sao
    adicionadas na ordem canonica. Tags existentes (declaradas via
    `openapi_tags` no construtor do FastAPI) sao preservadas mas re-ordenadas
    para que API_TAGS_ORDERED venha primeiro.

    Args:
        unique_existing: lista deduplicada de tag dicts ja no schema.

    Returns:
        Lista final mesclada para o OpenAPI.
    """
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for tag_dict in API_TAGS_ORDERED:
        merged.append(tag_dict)
        seen.add(tag_dict["name"])

    for tag in unique_existing:
        name = tag.get("name")
        if not name or name in seen:
            continue
        merged.append(tag)
        seen.add(name)

    return merged


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Gera OpenAPI schema enriquecido com metadata canonica.

    Idempotente: cacheia via `app.openapi_schema` (mesmo pattern do FastAPI).

    Args:
        app: instancia FastAPI.

    Returns:
        Schema OpenAPI 3.0+ enriquecido.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    info = openapi_schema.setdefault("info", {})
    info["contact"] = API_CONTACT
    info["license"] = API_LICENSE

    if info.get("title") in (None, "FastAPI"):
        info["title"] = "Cartorio Backend API"

    openapi_schema["servers"] = API_SERVERS

    existing_tags = openapi_schema.get("tags", []) or []
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for tag in existing_tags:
        name = tag.get("name") if isinstance(tag, dict) else None
        if name and name not in seen:
            unique.append(tag)
            seen.add(name)

    openapi_schema["tags"] = _merge_tags(unique)

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    for scheme_name, scheme_def in SECURITY_SCHEMES.items():
        security_schemes[scheme_name] = scheme_def

    _register_webhook_schemas(components)
    _enrich_sensitive_fields(openapi_schema)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _is_sensitive_name(name: str) -> bool:
    """Verifica se o nome de um campo OpenAPI indica dados sensíveis/PII."""
    name_lower = name.lower()
    sensitive_words = [
        "cpf",
        "cnpj",
        "rg",
        "email",
        "phone",
        "telefone",
        "password",
        "secret",
        "token",
        "jwt",
        "senha",
    ]
    if (
        name_lower == "ip"
        or "client_ip" in name_lower
        or "consent_ip" in name_lower
        or "ip_address" in name_lower
    ):
        return True
    for word in sensitive_words:
        if word in name_lower:
            return True
    return False


def _enrich_sensitive_fields(openapi_schema: dict[str, Any]) -> None:
    """Varre todos os schemas em components/schemas e injeta 'x-sensivel': True."""
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        return

    def process_properties(properties: dict[str, Any]) -> None:
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                continue

            if _is_sensitive_name(prop_name):
                prop_def["x-sensivel"] = True

            if "properties" in prop_def and isinstance(prop_def["properties"], dict):
                process_properties(prop_def["properties"])

            if "items" in prop_def and isinstance(prop_def["items"], dict):
                items_def = prop_def["items"]
                if "properties" in items_def and isinstance(items_def["properties"], dict):
                    process_properties(items_def["properties"])

    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            continue
        properties = schema_def.get("properties")
        if isinstance(properties, dict):
            process_properties(properties)


def _register_webhook_schemas(components: dict[str, Any]) -> None:
    """Force-register webhook schemas (G8.17.T2).

    Webhooks cobertos:
    - Telegram (Update/Message/User/Chat/CallbackQuery)
    - Evolution (Payload/Key/Message) - WhatsApp dual-format
    - Chatwoot (MessageCreated/ConversationStatusChanged)
    - N8N (ErrorRequest/DeletionRequest/MetricsIngest)
    - AlertManager (Payload/Entry/Label/Annotation) - ja auto-registrado
    - Outbox (DispatchRequest) - Supabase outbox
    """
    from app.schemas.webhook_payloads import (
        ChatwootConversationRef,
        ChatwootConversationStatusChanged,
        ChatwootMessageCreated,
        EvolutionKey,
        EvolutionMessage,
        EvolutionPayload,
        N8nDeletionRequest,
        N8nErrorRequest,
        N8nMetricsIngest,
        OutboxDispatchRequest,
        TelegramCallbackQuery,
        TelegramChat,
        TelegramMessage,
        TelegramUpdate,
        TelegramUser,
    )

    schemas = components.setdefault("schemas", {})
    force_register = [
        TelegramUpdate,
        TelegramMessage,
        TelegramUser,
        TelegramChat,
        TelegramCallbackQuery,
        EvolutionPayload,
        EvolutionKey,
        EvolutionMessage,
        ChatwootMessageCreated,
        ChatwootConversationStatusChanged,
        ChatwootConversationRef,
        N8nErrorRequest,
        N8nDeletionRequest,
        N8nMetricsIngest,
        OutboxDispatchRequest,
    ]
    def rewrite_local_refs(value: Any) -> Any:
        """Converte refs Pydantic locais em refs validos de components."""
        if isinstance(value, dict):
            rewritten: dict[str, Any] = {}
            for key, item in value.items():
                if key == "$ref" and isinstance(item, str) and item.startswith("#/$defs/"):
                    rewritten[key] = f"#/components/schemas/{item.removeprefix('#/$defs/')}"
                else:
                    rewritten[key] = rewrite_local_refs(item)
            return rewritten
        if isinstance(value, list):
            return [rewrite_local_refs(item) for item in value]
        return value

    for schema in force_register:
        try:
            raw_schema = deepcopy(schema.model_json_schema())  # type: ignore[attr-defined]
            definitions = raw_schema.pop("$defs", {})
            schemas[schema.__name__] = rewrite_local_refs(raw_schema)
            if isinstance(definitions, dict):
                for definition_name, definition in definitions.items():
                    schemas.setdefault(definition_name, rewrite_local_refs(definition))
        except Exception:  # noqa: BLE001
            continue

    schemas["ChatwootWebhookModel"] = {
        "oneOf": [
            {"$ref": "#/components/schemas/ChatwootConversationStatusChanged"},
            {"$ref": "#/components/schemas/ChatwootMessageCreated"},
        ]
    }


def install_openapi_enhancer(app: FastAPI) -> None:
    """Instala o hook `app.openapi` no FastAPI para customizar o schema.

    Apos instalar, GET /openapi.json retorna o schema enriquecido com
    info.contact + info.license + servers + tags ordenados + security schemes.

    Args:
        app: instancia FastAPI.
    """
    app.openapi_schema = None
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]
