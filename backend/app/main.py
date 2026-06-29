"""FastAPI app entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.api.v1.ws.atendimentos import ws_router
from app.config import settings
from app.db import engine, session_scope
from app.models.base import Base
from app.services.audit import AuditService
from app.services.rate_limit import RateLimitMiddleware
from app.services.rate_limit_by_key import RateLimitByKeyMiddleware
from app.services.tracing import init_tracing
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.slow_log import SlowLogMiddleware
from app.middleware.openapi_validator import install_openapi_validation_middleware
from app.middleware.version_header import VersionHeaderMiddleware, install_version_endpoint
from app.middleware.problem_details import install_problem_handlers
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.idempotency_store import RedisIdempotencyStore

logger = logging.getLogger(__name__)


async def _dead_mans_switch_loop() -> None:
    """Loop async do dead man's switch audit_log (A13).

    Roda a cada `settings.audit_dead_mans_switch_interval_minutes` (env
    `AUDIT_DEAD_MANS_SWITCH_INTERVAL_MINUTES`, default 15min). Executa
    `run_dead_mans_switch_check_3lvl()` que ja loga + envia Telegram
    se status != HEALTHY. Erros NAO derrubam o loop (best-effort).

    Fica cancelado via `task.cancel()` no shutdown.
    """
    from app.jobs.cron_dead_mans_switch import run_dead_mans_switch_check_3lvl

    interval_seconds = max(60, settings.audit_dead_mans_switch_interval_minutes * 60)
    # Sleep inicial curto pra nao derrubar startup se DB estiver lento
    await asyncio.sleep(30)
    while True:
        try:
            with session_scope() as db:
                result = run_dead_mans_switch_check_3lvl(db)
                logger.info(
                    "DEAD_MANS_SWITCH_TICK: status=%s alerted=%s telegram_sent=%s",
                    result.health.status.value,
                    result.alerted,
                    result.telegram_sent,
                )
        except Exception as exc:  # pragma: no cover - safety net
            logger.error(
                "DEAD_MANS_SWITCH_LOOP_ERROR: type=%s msg=%s",
                type(exc).__name__,
                str(exc)[:200],
            )
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Smoke test DB + create tables if missing + audit log init + tracing init (A3)."""
    # 0. OpenTelemetry tracing init (A3 — squad A)
    init_tracing("cartorio-api")
    # 1. Smoke test: confirm DB is reachable
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # 2. Create all tables (idempotent — no-op if schema already exists).
    # MVP-friendly: we don't have Alembic migrations set up yet, so we let
    # SQLAlchemy create the schema from the model metadata. Safe because
    # create_all() never drops or alters existing tables.
    Base.metadata.create_all(bind=engine)

    # 3. Audit log: write a startup entry (no-op if audit_log empty)
    AuditService.log_system_action("api.startup", {"version": "0.6.0", "env": settings.app_env})

    # 4. Dead man's switch scheduler in-process (A13)
    dms_task: asyncio.Task[None] | None = None
    if settings.audit_dead_mans_switch_minutes > 0:
        dms_task = asyncio.create_task(
            _dead_mans_switch_loop(),
            name="dead_mans_switch_loop",
        )
        logger.info(
            "DEAD_MANS_SWITCH_SCHEDULER_STARTED: interval=%dmin threshold=%dmin",
            settings.audit_dead_mans_switch_interval_minutes,
            settings.audit_dead_mans_switch_minutes,
        )

    try:
        yield
    finally:
        # Cancel scheduler
        if dms_task is not None:
            dms_task.cancel()
            try:
                await dms_task
            except asyncio.CancelledError:
                pass
        AuditService.log_system_action("api.shutdown", {})


# ============================================================================
# OpenAPI metadata polido (PT-BR, contato, licenca, terms)
# ============================================================================

API_DESCRIPTION = """
# Cartorio Backend API

API REST do **2o Servico Notarial de Uberlandia** para consulta de emolumentos,
protocolizacao de atos, gestao de atendimentos e auditoria imutavel.

## Pilares

- **Audit log imutavel**: hash chain SHA256 + HMAC. Cada acao deixa rastro verificavel.
- **PII scrubbing**: CPF/telefone/email nunca saem crus pra LLM. Hasheados no DB (SHA256+salt).
- **HITL obrigatorio**: protocolo sempre nasce em `DRAFT`. Escrevente valida antes de processar.
- **LGPD compliance**: consentimento explicito, retencao 365 dias (conversas) / 1825 (audit).
- **MCP nativo**: API expoe tools MCP via /mcp (protocolo 2025-03-26).

## Tags disponiveis (10 tags, 15 endpoints)

| Tag | Endpoints | Descricao |
|-----|-----------|-----------|
| `emolumento`  | 1   | Calculo de custas (TABELA_2026_MG) |
| `protocolo`   | 2   | Criar e consultar protocolos |
| `documento`   | 1   | Segunda via de documento |
| `audit`       | 1   | Verificacao de cadeia de audit log |
| `health`      | 2   | Liveness, readiness, radar |
| `atendimento` | 4   | Handoff humano + pesquisa satisfacao |
| `webhook`     | 2   | Integracao Evolution API / Chatwoot |
| `meta`        | 3   | Health, MCP servers discovery |
| `agendamento` | 1   | Disponibilidade de agenda |
| `dev`         | 1   | Exports (Postman collection) |

## Autenticacao

API em si **NAO exige auth** (LGPD art. 7o, IV - finalidade publica do servico notarial).
Para endpoints sensiveis (audit verify, webhook), usamos **HMAC ou header X-API-Key**
compartilhado com n8n (ver `N8N_WEBHOOK_SECRET` / `CARTORIO_API_KEY`).

## MCP (Model Context Protocol)

A propria API expoe tools MCP no endpoint `/mcp/mcp` (sub-app FastMCP montado, protocolo 2025-03-26).
Tools disponiveis:

1. `cartorio_calcular_emolumento` - calculo MG 2026
2. `cartorio_consultar_protocolo` - status, historico, proxima acao
3. `cartorio_criar_protocolo` - criar DRAFT com gate LGPD
4. `cartorio_gerar_segunda_via` - link download PDF
5. `cartorio_audit_verify` - integridade hash chain + HMAC
6. `cartorio_saudacao` - health check
7. `super_server_info` - meta info (versao, tools_count, etc)

Lista de tools em `/mcp-servers`. Config em `~/.mavis/mcp/clients/cartorio-mcp-config.json`.
Tools description em `/tools_description.json`.

## Compliance LGPD

- Art. 7o, I  - Consentimento explicito (gate no POST /protocolo)
- Art. 37    - Registro de operacoes de tratamento (audit log)
- Art. 46    - Medidas de seguranca (HMAC + hash chain)
- Retencao: 365 dias conversas, 1825 dias (5 anos) audit log
- DPO: dpo@2notasudi.com.br

## Stack

- **API**: FastAPI 0.115 + SQLAlchemy 2 + Pydantic 2 + Pydantic Settings
- **DB**: Supabase (PostgreSQL 15) via SQLAlchemy + Alembic
- **Cache/Session**: Redis 7
- **WhatsApp**: Evolution API (http://cartorio_evolution-api:8080)
- **CRM**: Chatwoot
- **Workflows**: n8n (https://cartorio-n8n.dfgdxq.easypanel.host)
- **LLM primario**: Opencode-Go (deepseek-v4-flash, low cost)
- **LLM secundario**: OpenClaw gateway (gpt-5.5 / anthropic-sonnet)
- **MCP**: FastMCP 3.4.2 (protocolo 2025-03-26)

## Contato

- DPO: dpo@2notasudi.com.br
- Repo: https://github.com/2notas/cartorio-backend
- Issues: https://github.com/2notas/cartorio-backend/issues
- Site: https://2notasudi.com.br
"""

API_TAGS_METADATA = [
    {
        "name": "emolumento",
        "description": "**Calculo de emolumentos** (TABELA_2026_MG). Publico, sem PII.",
    },
    {
        "name": "protocolo",
        "description": (
            "**Ciclo de vida do protocolo** (DRAFT → EM_ANDAMENTO → CONCLUIDO). "
            "HITL obrigatorio: protocolo sempre nasce em DRAFT."
        ),
    },
    {
        "name": "documento",
        "description": "**Emissao de segunda via** de documentos. v0.5.0 MVP retorna URL placeholder.",
    },
    {
        "name": "audit",
        "description": (
            "**Integridade do audit log** (hash chain SHA256 + HMAC). "
            "Recomendado rodar diariamente via cron `AUDIT_VERIFY_CRON`."
        ),
    },
    {
        "name": "health",
        "description": "**Health checks** (liveness, readiness, radar multi-servico).",
    },
    {
        "name": "atendimento",
        "description": (
            "**Handoff humano + pesquisa de satisfacao**. "
            "Integrado com Chatwoot e workflow n8n #07."
        ),
    },
    {
        "name": "webhook",
        "description": "**Integracao com canais externos** (Evolution API / WhatsApp, Chatwoot).",
    },
    {
        "name": "meta",
        "description": "**Endpoints de descoberta** (health, MCP servers).",
    },
    {
        "name": "agendamento",
        "description": "**Disponibilidade de agenda** dos escreventes.",
    },
    {
        "name": "dev",
        "description": "**Ferramentas de desenvolvimento** (Postman collection, etc).",
    },
]

API_CONTACT = {
    "name": "Cartorio 2 Notas Uberlandia",
    "url": "https://2notasudi.com.br",
    "email": "dpo@2notasudi.com.br",
}

API_LICENSE_INFO = {
    "name": "Proprietary - 2o Servico Notarial de Uberlandia",
    "url": "https://2notasudi.com.br/termos",
}


app = FastAPI(
    title="Cartorio Backend API",
    description=API_DESCRIPTION,
    version="0.5.4",
    contact=API_CONTACT,
    license_info=API_LICENSE_INFO,
    openapi_tags=API_TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# RFC 7807 Problem Details (A21 — squad A): handlers globais para
# HTTPException, RequestValidationError, e Exception generica.
# Converte {"detail": "..."} em application/problem+json estruturado.
# Ver tests/test_problem_details.py.
install_problem_handlers(app)

# OpenAPI validation helper (A19 — squad A): expoe schema + validators.
# Integracao completa (request/response middleware) sera feita em Sprint 5+
# com spectree. Por enquanto: log de paths/components detectados.
install_openapi_validation_middleware(app)

# API versioning (A20 — squad A): headers X-API-Version + Link (RFC 8594)
# + endpoint /version com metadata completa.
app.add_middleware(VersionHeaderMiddleware)
install_version_endpoint(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Headers de seguranca (A23 — squad A): HSTS, CSP, X-Frame-Options, etc.
app.add_middleware(SecurityHeadersMiddleware)

# Request context (audit metadata): popula request.state com request_id,
# client_ip, user_agent, canal e timestamp. LGPD art. 37 exige registro
# de operacoes de tratamento. Deve vir ANTES de RateLimit pra que rate
# limit tambem possa logar contexto se quiser.
app.add_middleware(RequestContextMiddleware)

# A6 — Idempotency-Key middleware (POST com header Idempotency-Key).
# Cacheia responses por 24h no Redis (SETNX) para evitar mutacoes duplicadas.
# LGPD: cache armazena apenas o response, sem PII. Chave = hash do header.
# Fail-open se Redis offline.
app.add_middleware(
    IdempotencyMiddleware,
    store=RedisIdempotencyStore(),
    paths_prefixes=("/api/v1/",),
    ttl_seconds=86400,
)

# Rate limiting por API key (T2.API.T22): protege /api/v1/* com 3 tiers
# (N8N 600/min, DPO 60/min, padrao 30/min). Coexiste com RateLimitMiddleware
# antigo (paths diferentes: /integrations/* + /admin/*). Fail-open se Redis
# offline. Ver tests/test_rate_limit_by_key.py. CHANGELOG v0.5.4.
app.add_middleware(
    RateLimitByKeyMiddleware,
    redis_url=settings.redis_url,
    api_key_header="x-api-key",
    paths_prefixes=("/api/v1/",),
)

# Rate limiting (T2.API.T21): protege /integrations/* + /admin/* contra
# abuso e cost overrun (LLM tokens, Evolution send, Chatwoot API).
# Redis sliding window 60/min por session_id (header X-Session-Id) ou
# hash do IP. Fail-open se Redis offline. Ver tests/test_rate_limit.py.
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.redis_url,
    per_minute=60,
    session_header="x-session-id",
    paths_prefixes=("/integrations/", "/admin/"),
)

# Slow request log (A15 — squad A): log estruturado para requests > 500ms.
# Skip automatico de /health/* e /metrics (ruido). Threshold via env
# SLOW_LOG_THRESHOLD_MS (default 500ms). Ver tests/test_slow_log.py.
app.add_middleware(SlowLogMiddleware, threshold_ms=500)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": settings.app_name, "version": "0.6.0"}


@app.get("/ready", tags=["meta"])
def ready() -> dict:
    """Readiness probe - confirma DB e audit log inicializados."""
    return {"status": "ready", "audit_chain_initialized": True}


@app.get("/", tags=["meta"], include_in_schema=False)
def root() -> dict:
    """Root - redireciona para Swagger UI."""
    return {
        "service": settings.app_name,
        "version": "0.6.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "mcp": "/mcp",
        "mcp_servers": "/mcp-servers",
    }


@app.get("/mcp-servers", tags=["meta"])
def mcp_servers() -> dict:
    """Lista MCP servers registrados (descoberta via mcp_config global).

    Retorna metadata dos 5 servers MCP disponiveis para clients
    (Antigravity, OpenCode, Claude Code, Zed):

    - n8n-mcp         : workflows N8N via MCP-HTTP
    - supabase-mcp    : Postgres + docs (config em ~/.gemini/antigravity/mcp_config.json)
    - cartorio-api    : esta propria API como MCP tools (backend/mcp_server.py)
    - easypanel-mcp   : controle do Easypanel (helbertparanhos/easypanel-mcp-server)
    - openclaw-mcp    : gateway OpenClaw para tools customizadas

    Config global: ~/.mavis/mcp/clients/cartorio-mcp-config.json
    """
    return {
        "status": "ok",
        "servers": [
            {
                "name": "cartorio-api",
                "transport": "http",
                "url": f"http://localhost:{settings.app_port}/mcp",
                "auth": "header: apikey",
                "tools_count": 7,
                "description": "API FastAPI como MCP tools (emolumento, protocolo, audit, segunda-via)",
                "path": "backend/mcp_server.py",
            },
            {
                "name": "n8n-mcp",
                "transport": "http",
                "url": settings.n8n_mcp_url,
                "auth": "header: Authorization: Bearer <jwt>",
                "tools_count": 50,
                "description": "Workflows N8N via MCP-HTTP",
            },
            {
                "name": "supabase-mcp",
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "auth": "oauth (auto)",
                "tools_count": 30,
                "description": "Postgres + docs Supabase (via ~/.gemini/antigravity/mcp_config.json)",
            },
            {
                "name": "easypanel-mcp",
                "transport": "stdio",
                "command": "easypanel-mcp-server",
                "auth": "env: EASYPANEL_API_URL + EASYPANEL_API_KEY",
                "tools_count": 57,
                "description": "Controle Easypanel (helbertparanhos/easypanel-mcp-server v2.0.0)",
            },
            {
                "name": "openclaw-mcp",
                "transport": "http",
                "url": "http://cartorio_openclaw-gateway:18789/v1/mcp",
                "auth": "header: Authorization: Bearer <gateway_token>",
                "tools_count": 20,
                "description": "OpenClaw gateway MCP (pendente Tailscale auth - SUI)",
            },
        ],
        "config_path": "~/.mavis/mcp/clients/cartorio-mcp-config.json",
        "version": "0.6.0",
    }


# ============================================================================
# MCP server mount (protocolo MCP 2025-03-26, http transport)
# ============================================================================

if settings.mcp_server_enabled:
    from mcp_server import mcp_app as _mcp_subapp_factory

    # Cria sub-app uma unica vez para extrair o lifespan
    _mcp_subapp = _mcp_subapp_factory()

    # IMPORTANTE: mescla o lifespan do MCP server no lifespan da FastAPI principal.
    # Sem isso, o StreamableHTTPSessionManager task group do FastMCP falha com
    # "task group is not initialized" em qualquer POST /mcp.
    # Ver https://gofastmcp.com/deployment/asgi
    @asynccontextmanager
    async def combined_lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        async with _mcp_subapp.router.lifespan_context(app_instance):
            async with lifespan(app_instance):
                yield

    app.router.lifespan_context = combined_lifespan

    # Monta o MCP server em /mcp/mcp (sub-app root + mount prefix)
    # Acesso: curl http://localhost:8000/mcp/mcp com headers MCP retorna JSON-RPC
    app.mount("/mcp", _mcp_subapp)


# ============================================================================
# Custom Swagger UI polish (titulo, tema, sintaxe PT-BR)
# ============================================================================

SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Cartorio Backend API - Swagger UI</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .topbar {{ display: none; }}
    .swagger-ui .info .title {{ color: #1a365d; font-size: 2.2em; }}
    .swagger-ui .info .description p {{ line-height: 1.6; }}
    .swagger-ui .opblock-tag {{ font-size: 1.15em; padding: 12px 16px; }}
    .swagger-ui .scheme-container {{ background: #f7fafc; padding: 14px 0; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .swagger-ui .btn {{ border-radius: 6px; }}
    .swagger-ui .opblock {{ border-radius: 8px; margin-bottom: 10px; }}
    .swagger-ui .opblock-summary {{ border-radius: 8px 8px 0 0; }}
    .header-cartorio {{
      background: linear-gradient(90deg, #1a365d 0%, #2c5282 100%);
      color: white;
      padding: 18px 32px;
      box-shadow: 0 2px 6px rgba(0,0,0,.15);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .header-cartorio h1 {{ margin: 0; font-size: 1.4em; font-weight: 600; }}
    .header-cartorio .links a {{ color: #cbd5e0; margin-left: 18px; text-decoration: none; }}
    .header-cartorio .links a:hover {{ color: white; text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="header-cartorio">
    <h1>Cartorio 2 Notas Uberlandia - Backend API</h1>
    <div class="links">
      <a href="/redoc">ReDoc</a>
      <a href="/openapi.json">openapi.json</a>
      <a href="/mcp">MCP</a>
      <a href="/mcp-servers">MCP Servers</a>
    </div>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {{
      window.ui = SwaggerUIBundle({{
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        docExpansion: 'list',
        filter: true,
        tryItOutEnabled: true,
        persistAuthorization: true,
        displayRequestDuration: true,
        syntaxHighlight: {{ theme: 'monokai' }},
        defaultModelsExpandDepth: -1,
      }});
    }};
  </script>
</body>
</html>
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Swagger UI customizado com header institucional e tema dark blue."""
    return HTMLResponse(SWAGGER_UI_HTML)


@app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    """ReDoc com branding institucional."""
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - ReDoc",
        redoc_favicon_url="https://2notasudi.com.br/favicon.ico",
    )


app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)  # WebSocket /ws/atendimentos (T2.API.T19)

# Telegram bot webhook (CartorioBot)
# Rota final: /api/v1/telegram/webhook
# (telegram.py ja tem prefix="/telegram" no router)
from app.api.v1.telegram import router as telegram_router  # noqa: E402

app.include_router(telegram_router, prefix="/api/v1")

# LGPD direitos do titular (Art. 18) - 5 endpoints + 1 ja em router.py
# Adicionado 2026-06-24 (anonimizar, corrigir, oposicao, optout, portabilidade)
from app.api.v1.lgpd_direitos import lgpd_router  # noqa: E402

app.include_router(lgpd_router, prefix="/api/v1")

# API v2 (alpha) - sunset 2027-12-31 (A24 SQUAD A versionamento)
from app.api.v2 import api_v2_router  # noqa: E402

app.include_router(api_v2_router, prefix="/api/v2")

# BRAIN endpoints (BRAIN6) - tarefas, lessons, sync, loop-state
from app.api.v1.brain import brain_router  # noqa: E402

app.include_router(brain_router, prefix="/api/v1")
