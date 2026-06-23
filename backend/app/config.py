"""Configuracao da aplicacao via env vars (Pydantic Settings v2).

Cobre TODOS os backends do cartorio:
- Database (Supabase)
- Redis (cache + sessoes)
- LLM providers (Opencode-Go, OpenClaw, OpenAI, Anthropic) — LiteLLM removido
- Evolution API (WhatsApp)
- Chatwoot (CRM atendimento humano)
- n8n (workflows)
- Audit log + PII

Convencao: `Optional[T] = None` significa que o servico desabilita se nao setado.
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # Aplicacao
    # ========================================================================
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "cartorio-backend"
    app_port: int = 8000
    log_level: str = "INFO"

    # ========================================================================
    # Database (Supabase - container db:5432 na rede cartorio_supabase_default)
    # ========================================================================
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # ========================================================================
    # Redis (cartorio_redis na porta 6379 interna, 1001 no host)
    # ========================================================================
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl_seconds: int = 86400  # 24h para sessoes WhatsApp

    # ========================================================================
    # Audit log
    # ========================================================================
    audit_hmac_key: str = Field(min_length=32)
    audit_verify_cron: str = "0 3 * * *"  # Diario as 03:00

    # ========================================================================
    # PII scrubbing
    # ========================================================================
    pii_scrub_enabled: bool = True
    pii_block_on_detect: bool = True  # bloqueia fluxo se PII detectado antes do LLM

    # ========================================================================
    # LLM providers
    # Opencode-Go (DeepSeek-v4 flash) = low cost primario
    # OpenClaw gateway = secundario (gpt-5.5 ou Anthropic)
    # LiteLLM removido (hackeado em 2026-06)
    # ========================================================================
    opencode_go_api_key: Optional[str] = None
    opencode_go_base_url: str = "https://api.opencode.ai/v1"  # placeholder
    opencode_go_model: str = "deepseek-v4-flash"
    opencode_go_rate_limit_per_minute: Optional[int] = None  # None = sem rate limit

    openclaw_base_url: str = "http://cartorio_openclaw-gateway:18790"
    openclaw_api_key: Optional[str] = None
    openclaw_model_primary: str = "gpt-5.5"
    openclaw_model_fallback: str = "anthropic/claude-sonnet-4.6"

    llm_default_provider: Literal["opencode_go", "openclaw"] = "opencode_go"

    # ========================================================================
    # Evolution API (WhatsApp)
    # ========================================================================
    evolution_base_url: str = "http://cartorio_evolution-api:8080"
    evolution_api_key: Optional[str] = None
    evolution_instance: str = "cartorio-2notas"

    # ========================================================================
    # Chatwoot (CRM / atendimento humano)
    # ========================================================================
    chatwoot_base_url: Optional[str] = None
    chatwoot_api_key: Optional[str] = None
    chatwoot_account_id: Optional[int] = None
    chatwoot_inbox_id: Optional[int] = None

    # ========================================================================
    # Webhook signature secrets (HMAC-SHA256, opcional mas recomendado em prod)
    # ========================================================================
    chatwoot_webhook_secret: Optional[str] = None
    evolution_webhook_secret: Optional[str] = None

    # ========================================================================
    # Stale detector (atendimento sem update > N min vira flag 'stale')
    # ========================================================================
    stale_threshold_minutes: int = 30

    # ========================================================================
    # n8n (workflows)
    # ========================================================================
    n8n_base_url: str = "http://cartorio_n8n:5678"
    n8n_api_key: Optional[str] = None
    n8n_mcp_url: str = "https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http"
    n8n_webhook_secret: Optional[str] = None

    # ========================================================================
    # Inter-service auth (API <-> N8N/Admin)
    # Header X-API-Key. Rotacao 90d (ADR-017).
    # =========================================================================
    cartorio_api_key: Optional[str] = None

    # ========================================================================
    # Supabase (acesso direto alem do DB)
    # ========================================================================
    supabase_url: str = "https://supbase.2notasudi.com.br"  # DNS typo original
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # ========================================================================
    # LGPD
    # ========================================================================
    dpo_email: str = "dpo@2notasudi.com.br"
    retention_days_conversas: int = 365
    retention_days_audit: int = 1825  # 5 anos

    # ========================================================================
    # CORS
    # ========================================================================
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "https://admin.2notasudi.com.br",
            "https://app.2notasudi.com.br",
        ]
    )

    # ========================================================================
    # MCP server (expõe tools MCP da API)
    # ========================================================================
    mcp_server_enabled: bool = True
    mcp_server_transport: Literal["stdio", "http"] = "http"
    mcp_server_port: int = 8100
    mcp_api_key: Optional[str] = None  # Bearer token pra clients MCP


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()