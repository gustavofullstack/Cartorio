# 🧠 SUPER PROMPT 2 — EASYPANEL + DOCKER SWARM + UDIA PODS
# ═══════════════════════════════════════════════════════════════════════════════
# VERSÃO: 2.1 (ATUALIZADO 2026-07-20)
# AUTOR: Gustavo Almeida
# PROJETO: Cartório 2º Notas Uberlândia — Infraestrutura Multi-Tenant
# AMBIENTE: Easypanel v2.32.0 + Docker Swarm + Tailscale
# VPS: 100.99.172.84:3000 (Tailscale tail2fe279.ts.net)
# CLASSIFICAÇÃO: DOCUMENTO MESTRE — INFRASTRUCTURE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

> **Fonte absoluta:** `prompt-2.json` (635+ linhas estruturadas)
> **Gerado automaticamente em:** 2026-07-02 17:57 BRT por /goal master intent
> **Atualizado em:** 2026-07-20 (v2.1 — estado de infra e topologia)
> **Convenção:** append-only. Sincronizar com JSON a cada mudança.

---

## 🟢 ESTADO ATUAL — 2026-07-20 (v2.1)

| Item | Valor validado |
|---|---|
| HEAD `origin/master` | `6967b71` (telegram fix `d642e0e` + zen 3 contas `bc9823c`) |
| Swarm produção | **19 serviços 1/1** na VPS (cartorio_api, chatwoot, evolution-api, lobechat, n8n, openclaw-gateway, redis, supabase pgvector pg17, traefik, etc.) |
| VPS acesso estável | `vps-public` = 187.77.236.77 (root) — preferir; `vps` = 100.99.172.84 (Tailscale) **instável** |
| Execução | VPS do Cartório (`vps`/`vps-public`) — não usar runner local externo |
| MacBook | somente cliente SSH — nunca carga pesada |
| Telegram | `@test_cartorio_bot` validado em prod 2026-07-20 (`response_sent=true`, secret OK, pending=0) |
| LLM | 3 contas OpenCode Zen integradas (slots coerentes, timeout 45s, payload por provider, fallback determinístico + circuit breaker) |
| Segredos | cofre `~/.mavis/secrets` **inexistente** — usar `.env`/`.secrets` gitignored + envs EasyPanel |
| SSH | sempre `-o ConnectTimeout=8 -o BatchMode=yes`, comandos únicos bounded — proibido interativo/loop/`tail -f` sem limite |

---

## 📋 ÍNDICE COMPLETO

- BLOCO 0 — Meta e Filosofia
- BLOCO 1 — Sistema
- BLOCO 2 — Design System
- BLOCO 3 — Infraestrutura
- BLOCO 4 — Serviços (24 ativos)
- BLOCO 5 — MCP Servers (3 ativos)
- BLOCO 6 — Agentes
- BLOCO 7 — Tasks
- BLOCO 8 — Plans
- BLOCO 9 — Goals
- BLOCO 10 — Objectives
- BLOCO 11 — Plugins (13)
- BLOCO 12 — Commands (12)
- BLOCO 13 — Tools
- BLOCO 14 — Deploy
- BLOCO 15 — Envs (13 required)
- BLOCO 16 — Memory (5 entries)
- BLOCO 17 — Progress
- BLOCO 18 — Index
- BLOCO 19 — Harness
- BLOCO 20 — Versionamento

---

# BLOCO 0 — META E FILOSOFIA

## 0.1 — O Que É Este Prompt

Documento mestre da **camada de infraestrutura** do projeto Cartório.
Complementa `PROMPT.MD` (camada aplicação/API) com:
- Easypanel v2.32.0 + Docker Swarm (24 serviços)
- MCP servers (3 ativos)
- Hierarquia agentes (3 níveis)
- Planos 4 fases (Learn → Integrate → Optimize → Document)
- Tools, plugins, commands, deploy, memory, harness

**Diferença PROMPT.MD vs PROMPT-2.MD:**
- PROMPT.MD = lógica negócio + APIs + squads + LGPD
- PROMPT-2.MD = infraestrutura + serviços + tools + automation

## 0.2 — Filosofia

```
1. APRENDER → INSTALAR → TESTAR → CORRIGIR → INTEGRAR → MELHORAR
   → OTIMIZAR → ORGANIZAR → DOCUMENTAR → COMENTAR → SALVAR
2. NUNCA apagar código sem melhorar/refatorar
3. NUNCA criar do zero o que já existe
4. EVOLUIR não DESTRUIR
5. NENHUM commit sem aprovação prévia do Gustavo no painel admin Udiapods
```

---

# BLOCO 1 — SISTEMA

| Campo | Valor |
|---|---|
| Role | SUPER_AGENT_ORQUESTRADOR |
| Mode | FULL_AUTONOMY_WITH_APPROVAL |
| Language | pt-BR |
| Max Steps | 25 |
| Memory Enabled | true |

**Skills Loaded:** kimi-help-center, kimi-widget

---

# BLOCO 2 — DESIGN SYSTEM

## Glassmorphism
- Enabled: true
- Backdrop filter: blur(20px)
- Containers: translúcidos

## Cores e Tipografia
```
PRIMARY   #FF6B35  laranja quente
SUCCESS   #00C853  verde vibrante
INFO      #2979FF  azul royal
ACCENT    #FF4081  rosa pink
BACKGROUND glassmorphism
FONTS     Poppins, Inter
BORDERS   12px (nunca 0px nem 50%)
SPACING   Fibonacci
CONTRAST  WCAG AA
```

**Regras:** proibição de maiúsculo em massa, neon apenas no padrão definido.

---

# BLOCO 3 — INFRAESTRUTURA

## 3.1 — Easypanel + Docker Swarm

| Item | Valor |
|---|---|
| Easypanel | v2.32.0 @ 100.99.172.84:3000 |
| Status | ativo |
| License | community (monitoramento avançado requer licença) |
| Docker Swarm | enabled, project cartorio, 24 services |

## 3.2 — Tailscale Network (tail2fe279.ts.net)

| Node | IP | Status |
|---|---|---|
| macbook-pro-gus | 100.83.180.16 | online |
| iphone-17-pro | 100.122.101.33 | online |
| iphone-andre | 100.74.36.41 | online |
| iphone-henrique | 100.76.109.91 | online |
| macbook-air-henrique | 100.122.88.49 | offline 37min |
| pc-do-andre | 100.112.202.91 | online (Windows) |
| triqhub | 100.110.127.44 | online (exit node) |
| **vps-cartorio** | **100.99.172.84** | **active direct** |

## 3.3 — Networking e Segurança

| Item | Valor |
|---|---|
| Proxy | ativo (Traefik + Let\'s Encrypt) |
| DNS | Cloudflare configurado |
| TLS | 1.3 |
| Encryption | AES-256 |
| Certificados | Let\'s Encrypt / Custom |
| SSH | habilitado (Tailscale + chave ed25519) |

---

# BLOCO 4 — SERVIÇOS (24 ativos)

## 4.1 — AI/LLM (4 serviços)

### anything-llm — ativo (verde)
- Workspace LLM multi-tenant
- Provider: Ollama / OpenAI / Anthropic
- Fallback: true

### lobechat — ativo (verde)
- Chat UI multi-provider
- Providers: OpenAI, Anthropic, Google, Ollama, DeepSeek

### openclaw-gateway — ativo (verde)
- Gateway MCP para OpenClaw
- Tiers: primary, fallback, economy
- Circuit breaker: true

### zeroclaw — ativo (verde)
- Agent terminal CLI
- Mode: autonomous with approval

## 4.2 — Gateway/Proxy (3 serviços)

### litellm-app — ativo (verde)
- Proxy multi-provider LLM
- Features: load_balancing, fallback, rate_limiting, cost_tracking
- Providers: OpenAI, Anthropic, Google, DeepSeek, Ollama

### litellm-db (postgres) — ativo (verde)
- Persistência logs/costs LiteLLM

### evolution-api — ativo (verde)
- Gateway WhatsApp multi-instância
- Features: webhooks, REST API, TypeBot, Chatwoot

## 4.3 — Chat/CRM (2 serviços)

### chatwoot — ativo (verde)
- Inbox multi-canal (WhatsApp, Email, Web)
- Features: human_handoff, labels, macros, reports

### chatwoot-sidekiq — ativo (verde)
- Background jobs Chatwoot

## 4.4 — Observability (6 serviços)

| Serviço | Função |
|---|---|
| langfuse-web | Observability LLM (traces, metrics, evals) |
| langfuse-worker | Processamento assíncrono |
| langfuse-db (postgres) | Banco Langfuse |
| langfuse-redis | Cache/fila Langfuse |
| langfuse-minio | Storage S3-compatível |
| langfuse-clickhouse | Analytics time-series |

## 4.5 — Data Labeling (5 serviços)

| Serviço | Função |
|---|---|
| argilla-web | UI labeling/feedback humano |
| argilla-db (postgres) | Banco Argilla |
| argilla-redis | Cache Argilla |
| argify-worker | Worker assíncrono Argilla |
| argilla-elasticsearch | Busca full-text |

## 4.6 — Database

### supabase (postgres) — ativo (verde)
- Banco principal (Auth, Realtime, Storage)
- Features: Row Level Security, Realtime, Storage

### redis — ativo (separado, no swarm)
- Cache global / Session store / Fila

## 4.7 — Notebook/Crawling/API (3 serviços)

### open-notebook — ativo (verde)
- Jupyter-like para experimentos

### open-notebook-surrealdb — ativo (verde)
- Banco SurrealDB para notebooks

### crawl4ai — ⚠️ alerta (amarelo)
- Web scraping para RAG
- Issue: VXLAN swarm bug (lesson 123/126)
- Workaround: restart swarm worker node ou recriar service com --network host

### api (cartório-api) — ativo (verde)
- API principal do projeto

---

# BLOCO 5 — MCP SERVERS (3 ativos)

| Server | Tools |
|---|---|
| openclaw-gateway | file_system, terminal, web_search, code_execution |
| evolution-api | send_message, receive_webhook, manage_instance |
| supabase | query, insert, update, delete, realtime_subscribe |

---

# BLOCO 6 — AGENTES

## 6.1 — Hierarquia

```
LEVEL 1: SUPER_AGENT_ORQUESTRADOR (este prompt)

LEVEL 2: 4 sub-orchestrators
  ├─ AGENT_LLM_ROUTER       roteia entre providers
  ├─ AGENT_CHATBOT          interação usuário via WhatsApp
  ├─ AGENT_CARTORIO         lógica de negócio cartorária
  └─ AGENT_OBSERVABILITY    monitoramento e alertas

LEVEL 3: 5 sub-agents
  ├─ SUBAGENT_FALLBACK      gerencia fallback entre LLMs
  ├─ SUBAGENT_RAG           retrieval augmented generation
  ├─ SUBAGENT_MEMORY        gerenciamento de memória/contexto
  ├─ SUBAGENT_COMPLIANCE    validação LGPD/cartório
  └─ SUBAGENT_HUMAN_HANDOFF escalonamento humano
```

## 6.2 — Comunicação

| Item | Valor |
|---|---|
| Protocol | MCP (Model Context Protocol) |
| Message Format | JSON-RPC 2.0 |
| Persistence | Redis + PostgreSQL |

---

# BLOCO 7 — TASKS

## Automation Rules

| Trigger | Action | Fallback | Timeout |
|---|---|---|---|
| mensagem_whatsapp_recebida | AGENT_CHATBOT.processar() | AGENT_HUMAN_HANDOFF.escalar() | 30s |
| llm_provider_offline | SUBAGENT_FALLBACK.trocar_provider() | SUBAGENT_FALLBACK.usar_local_ollama() | 10s |
| acao_critica_cartorio | SUBAGENT_COMPLIANCE.validar() | AGENT_HUMAN_HANDOFF.aprovar() | indefinido |

---

# BLOCO 8 — PLANS

## Phase 1: Learn (1-2 dias)
- Mapear todas APIs dos serviços ativos
- Documentar endpoints
- Testar conectividade
- Verificar .envs

## Phase 2: Integrate (3-5 dias)
- Conectar Evolution-API → Chatwoot
- Conectar LiteLLM → todos providers
- Configurar fallback entre LLMs
- Integrar Langfuse para observability

## Phase 3: Optimize (5-7 dias)
- Otimizar latência entre serviços
- Configurar cache Redis eficiente
- Ajustar circuit breakers
- Implementar health checks

## Phase 4: Document (2-3 dias)
- Documentar arquitetura completa
- Criar runbooks de operação
- Documentar procedimentos de fallback
- Criar guia de troubleshooting

---

# BLOCO 9 — GOALS

**Primary:** Chatbot autônomo para cartório com 99.9% uptime

**Secondary:**
- Resposta < 2s para queries simples
- Fallback automático em < 5s
- Human handoff em < 30s
- Compliance LGPD 100%
- Custo LLM otimizado (tier economy quando possível)

---

# BLOCO 10 — OBJECTIVES

## Short Term (próximas 2 semanas)
- [ ] Corrigir status amarelo do crawl4ai (VXLAN workaround)
- [ ] Verificar configuração de .envs em todos serviços
- [x] Testar fallback LLM entre providers (9 E2E logs + 3 fallback stress) ✅
- [ ] Validar integração Evolution-API ↔ Chatwoot

## Medium Term (1-2 meses)
- [ ] Implementar RAG com documentos cartorários
- [ ] Configurar Argilla para feedback humano
- [ ] Implementar evals automáticos no Langfuse
- [ ] Criar dashboard de métricas

## Long Term (3-6 meses)
- [ ] Automação completa de certidões
- [ ] Integração com sistemas oficiais (Registro Civil)
- [ ] Multi-tenant para múltiplos cartórios
- [ ] IA preditiva para demanda

---

# BLOCO 11 — PLUGINS (13 ativos)

```
kimi-help-center, kimi-widget, mcp-server-client, web_search,
web_open_url, ipython, get_data_source, memory_instruction_edits,
add_cron_job, list_cron_jobs, update_cron_job, remove_cron_job
```

---

# BLOCO 12 — COMMANDS (12 disponíveis)

```
web_search, web_open_url, search_image_by_text, search_image_by_image,
ipython, get_data_source_desc, get_data_source, memory_instruction_edits,
add_cron_job, list_cron_jobs, update_cron_job, remove_cron_job
```

**Usage Rules:**
- Sempre web_search antes de web_open_url
- ipython para computação/análise/gráficos
- Salvar resultados em /mnt/agents/output/
- Nunca expor memory_id ao usuário

---

# BLOCO 13 — TOOLS

## Terminal
- Access: SSH/Tailscale
- IP: 100.99.172.84
- Commands: docker, docker-compose, docker-swarm, ssh, tailscale

## SSH
- Target: 100.99.172.84:3000
- Auth: Tailscale + SSH key

## Proxy
- Type: reverse_proxy
- Handles: SSL termination, load balancing, rate limiting

## DNS
- Provider: configurado
- Records: apontando para 100.99.172.84

## Cryptography
- TLS: 1.3
- Encryption: AES-256
- Certificates: Let\'s Encrypt / Custom

---

# BLOCO 14 — DEPLOY

| Item | Valor |
|---|---|
| Platform | Easypanel + Docker Swarm |
| Hosting | Hostinger (187.77.236.77) |
| CI/CD | Easypanel built-in |
| Rollback | Docker Swarm service rollback |

### Backup
- Postgres: automático via Easypanel
- Redis: RDB snapshots
- Volumes: Docker volumes persistentes

---

# BLOCO 15 — ENVS (13 required vars)

| Var | Required |
|---|---|
| OPENAI_API_KEY | ✅ |
| ANTHROPIC_API_KEY | ✅ |
| GOOGLE_API_KEY | ✅ |
| DEEPSEEK_API_KEY | ✅ |
| EVOLUTION_API_KEY | ✅ |
| CHATWOOT_API_KEY | ✅ |
| SUPABASE_URL | ✅ |
| SUPABASE_KEY | ✅ |
| REDIS_URL | ✅ |
| POSTGRES_URL | ✅ |
| LITELLM_MASTER_KEY | ✅ |
| LANGFUSE_PUBLIC_KEY | ✅ |
| LANGFUSE_SECRET_KEY | ✅ |

**Location:** /mnt/agents/upload/ ou variáveis Easypanel
**Security:** nunca expor em logs ou commits

---

# BLOCO 16 — MEMORY

| Item | Valor |
|---|---|
| System | memory_instruction_edits |
| Max Entries | 50 |

### Rules:
- Só salvar quando usuário pedir explicitamente
- Nunca salvar dados de menores (<18)
- Nunca salvar: raça, etnia, religião, criminal, localização precisa, política, saúde
- Usar mesma linguagem do usuário

### Current Entries (5):
1. Proibição commits sem aprovação prévia no admin Udiapods
2. Design system Udiapods (glassmorphism, cores, fontes)
3. Painel admin Udiapods V2 (React+Vite+TS)
4. Bugs críticos pendentes no admin
5. FinanceApp OS em /mnt/agents/output/finance-app-os/

---

# BLOCO 17 — PROGRESS

```
CURRENT_PHASE: Phase 1 - LEARN

COMPLETED:
  - Easypanel instalado e configurado
  - 24 serviços Docker Swarm ativos
  - Tailscale configurado
  - LiteLLM proxy ativo
  - Evolution-API gateway WhatsApp ativo
  - Chatwoot inbox ativo

IN_PROGRESS:
  - Mapeamento completo de APIs
  - Configuração de fallback LLM
  - Integração Evolution-API ↔ Chatwoot

PENDING:
  - RAG com documentos cartorários
  - Evals automáticos Langfuse
  - Dashboard de métricas
  - Automação certidões
```

---

# BLOCO 18 — INDEX

## Services by Function

```
ai_conversation: anything-llm, lobechat, openclaw-gateway, zeroclaw
ai_gateway: litellm-app, evolution-api
crm_chat: chatwoot, chatwoot-sidekiq
observability: langfuse-{web,worker,db,redis,minio,clickhouse}
data_labeling: argilla-{web,db,redis,worker,elasticsearch}
database: supabase, redis, litellm-db, open-notebook-surrealdb
crawling: crawl4ai
notebook: open-notebook
api: api (cartório-api)
```

---

# BLOCO 19 — HARNESS

## 19.1 — LLM Routing

```
PRIMARY:     anthropic/claude-sonnet-4-6
FALLBACK_1:  openai/gpt-4o
FALLBACK_2:  google/gemini-2.5-pro
ECONOMY:     deepseek/deepseek-chat
LOCAL:       ollama/llama3.3:70b
```

## Circuit Breaker

| Param | Valor |
|---|---|
| failure_threshold | 5 |
| recovery_timeout | 60s |
| health_check_interval | 30s |

## Cost Optimization

| Tipo | Tier |
|---|---|
| simple_queries | economy |
| complex_queries | primary |
| critical_actions | primary + human approval |
| batch_processing | local |

---

# BLOCO 20 — VERSIONAMENTO

## 20.1 — Changelog

```
v2.0 (2026-07-02 17:57 BRT) — RECONSTRUÍDO a partir de prompt-2.json
  - Conversão 1:1 JSON → Markdown estruturado
  - 20 blocos organizados (era apenas manifesto de 12 linhas)
  - Adicionado frontmatter + changelog
  - Backup do antigo: prompt-2.md.bak.20260702_175737
  - Sincronização: regenerar este MD a cada update do JSON

v1.0 (2026-07-02T12:39:00Z) — original manifesto de 12 linhas
  - Criação inicial (apenas meta + comandos básicos)
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# FIM DO PROMPT-2 v2.0
# Próxima revisão: quando prompt-2.json for atualizado
# Owner: cartorio-dev + cartorio-lgpd (review LGPD compliance)
# ═══════════════════════════════════════════════════════════════════════════════
