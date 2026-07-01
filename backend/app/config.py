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
    # Pool tuning A15 — defaults calibrados pra carga real (chatbot + N8N + admin
    # simultaneos). Total = pool_size + max_overflow = 30 conexoes. Pre-ping detecta
    # stale; recycle 1h evita conexao morta em pgBouncer/LB.
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600  # 1h — recicla conexao antes de timeouts silenciosos
    db_pool_timeout: int = 30  # 30s na fila ate TimeoutError se pool saturado
    db_pool_pre_ping: bool = True  # testa SELECT 1 antes de cada checkout

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

    # Dead man's switch (A13): se audit_log ficar stale > N min, alerta Telegram
    # GRUPO PIETRA SQUAD. Default 60min = continuidade auditoria LGPD art. 37.
    audit_dead_mans_switch_minutes: int = 60
    audit_dead_mans_switch_interval_minutes: int = 15  # freq do scheduler in-process
    # Chat ID Telegram GRUPO PIETRA SQUAD para alertas do dead man's switch.
    # Vazio = nao envia (apenas loga). Sprint 5 integra com TelegramBot real.
    audit_alert_telegram_chat_id: Optional[str] = None
    # Telegram Bot Token (usado por NotificationService para enviar msgs a clientes).
    # Mesmo bot de testes @test_cartorio_bot — em produção, separar.
    telegram_bot_token: Optional[str] = None

    # ========================================================================
    # PII scrubbing
    # ========================================================================
    pii_scrub_enabled: bool = True
    pii_block_on_detect: bool = True  # bloqueia fluxo se PII detectado antes do LLM

    # ========================================================================
    # LLM providers (chain completo Turno 37 2026-06-30)
    # opencode_go (DeepSeek-v4 flash) = primario
    # openclaw = secundario
    # openrouter, groq, mistral, opencode-free-2/3, google_ai_studio, jules = fallbacks
    # ========================================================================
    # Primary
    opencode_go_api_key: Optional[str] = None
    opencode_go_base_url: str = "https://opencode.ai/zen/v1"
    opencode_go_model: str = "deepseek-v4-flash-free"
    opencode_go_rate_limit_per_minute: Optional[int] = None
    # Thinking mode (T57 E08) — controla `thinking` field no payload Chat Completions.
    # Valores: "disabled" (sem thinking), "enabled" (force on), "adaptive" (provider decide — default).
    # DeepSeek-v4-flash e MiniMax-M3 suportam "adaptive" com 1M context.
    opencode_go_thinking_mode: Literal["disabled", "enabled", "adaptive"] = "adaptive"

    # Opencode-Free-1 (nemotron-3-ultra-free, 1M ctx) - Turno 37
    opencode_free_1_api_key: Optional[str] = None
    opencode_free_1_model: str = "nemotron-3-ultra-free"
    opencode_free_1_base_url: str = "https://opencode.ai/zen/v1"

    # Opencode-Free-2 (mimo-v2.5-free, 1M ctx) - Turno 37
    opencode_free_2_api_key: Optional[str] = None
    opencode_free_2_model: str = "mimo-v2.5-free"
    opencode_free_2_base_url: str = "https://opencode.ai/zen/v1"

    # Opencode-Free-3 (deepseek-v4-flash-free, 1M ctx) - Turno 37 (default)
    opencode_free_3_api_key: Optional[str] = None
    opencode_free_3_model: str = "deepseek-v4-flash-free"
    opencode_free_3_base_url: str = "https://opencode.ai/zen/v1"

    # Mistral (devstral-small-latest, 256K ctx) - Turno 37
    mistral_api_key: Optional[str] = None
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "devstral-small-latest"

    # OpenRouter (multi-model aggregator) - Turno 37
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemma-4-31b-it:free"

    # Groq (compound, 131K ctx) - Turno 37
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "groq/compound"

    # Google AI Studio (gemini-3.5-flash, 1M ctx) - Turno 37
    google_ai_studio_api_key: Optional[str] = None
    google_ai_studio_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    google_ai_studio_model: str = "gemini-3.5-flash"

    # OpenClaw (gpt-5.5 fallback legacy)
    openclaw_base_url: str = "http://cartorio_openclaw-gateway:18790"
    openclaw_api_key: Optional[str] = None
    openclaw_model_primary: str = "gpt-5.5"
    openclaw_model_fallback: str = "anthropic/claude-sonnet-4.6"

    # Jules (Google Gemini 3.1 Pro via async API) - Turno 35/37
    jules_api_key: Optional[str] = None
    jules_base_url: str = "https://jules.googleapis.com/v1alpha"

    # Antigravity (Gemini via OAuth2 stored token) - Turno 38
    antigravity_token: Optional[str] = None  # null = use keyring/file
    antigravity_base_url: str = "https://antigravity.googleapis.com/v1"
    antigravity_default_model: str = "gemini-3.1-pro"

    # Chain order (try in sequence). Tweak LLM_FALLBACK_CHAIN env to override
    llm_default_provider: str = "opencode_free_3"
    llm_fallback_chain: str = (
        "opencode_free_3,opencode_free_1,opencode_free_2,"
        "opencode_go,openrouter,groq,mistral,"
        "google_ai_studio,openclaw,jules,antigravity"
    )
    # Thinking mode global (T57 E08) — default se provider-specific nao setar.
    # "adaptive" deixa provider decidir quando usar thinking (recomendado p/ 1M ctx).
    llm_thinking_mode: Literal["disabled", "enabled", "adaptive"] = "adaptive"

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
    telegram_webhook_secret: Optional[str] = None

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
    # Validacao strict: 64 chars hex lowercase (= `openssl rand -hex 32`).
    # FAIL-FAST: se ausente, tamanho errado OU formato invalido, app nao sobe
    # (B0.3 2026-06-25 + LGPD review P1.1 2026-06-25).
    # =========================================================================
    cartorio_api_key: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )

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
    # Retencao scheduler in-process (Sprint 3 G4.3 - ADR-019).
    # Roda `run_retencao()` diariamente no horario configurado.
    # - retencao_enabled=False desativa o scheduler (job manual via /admin/retencao/run)
    # - retencao_hour_brazil eh em BRT (UTC-3), convertido internamente
    retencao_enabled: bool = True
    retencao_hour_brazil: int = 3  # 03:00 BRT = 06:00 UTC daily

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

    # ========================================================================
    # JWT (A24 API v2) — usado por /api/v2/* alem de X-API-Key v1
    # HS256 com secret em env. Validade 60min access + 7d refresh.
    # FAIL-FAST: secret DEVE ter min 32 chars (HMAC-SHA256 requirement).
    # ========================================================================
    jwt_secret: Optional[str] = None  # FAIL-FAST no service: precisa ter min 32 chars se usado
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 7
    jwt_issuer: str = "cartorio-api"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
