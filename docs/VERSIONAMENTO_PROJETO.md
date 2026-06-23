# VERSIONAMENTO — Cartório AI OS

> **Índice rápido** pra qualquer agent (Mavis, coders, LGPD) pegar contexto em < 2min.
> Pra detalhes, ler: `docs/CHANGELOG.md` (granular) + `docs/ROADMAP.md` (12 semanas) + `docs/SUPER_PLAN.md` (visão macro).

---

## 🎯 ONDE ESTAMOS (snapshot 2026-06-23 13:55 BRT)

```
VERSÃO ATUAL:        v0.4.3
FASE:                Fase 0 → Fase 1 (transição)
SPRINT ATUAL:        Sprint 1 — API Protocolo + LGPD Gate (concluído)
PRÓXIMO SPRINT:      Sprint 1.1 — Backup + Workflows (em hardening)
RADAR:               GREEN (com ressalvas — ver "RESSALVAS" abaixo)
```

### RESSALVAS (verdade nua)
- ✅ Infra: 12 containers Swarm UP, todos domínios respondendo, MCP server /mcp/mcp OK
- ✅ OpenClaw: health 200 OK, Tailscale VPN OK, UI HTML servida em /v1/agents
- ❌ **OpenClaw /v1/chat POST retorna 404** — rota não implementada na v0.4.0 (real gap que Gustavo reclamou)
- ✅ N8N: 4 creds (opencode-go, supabase, cartorio-api, evolution-api) + 11 WFs ativos
- ⚠️ **5 WFs duplicatas "11-Monitor Cartório" inativos** (cartorio-n8n vai deletar)
- ✅ API: FastAPI 0.4.0, Swagger PT-BR, 18 endpoints, MCP server carregado
- ✅ Chatwoot: conectado Supabase+Redis
- ✅ Supabase: 15 services HEALTHY (db, auth, rest, storage, kong, studio, etc)
- ❌ **Subdomínios Tailscale (*.tail2fe279.ts.net) NÃO respondem** (000) — precisa cert + Traefik router
- ⚠️ **Opencode-Go in-line no router.py** (linhas 475-518), falta módulo dedicado (cartorio-dev tá fazendo)

---

## 📦 HISTÓRICO DE VERSÕES (resumo)

| Versão | Data | Sprint | Status | Resumo |
|--------|------|--------|--------|--------|
| **v0.4.3** | 2026-06-23 15:00 | 1.3 | ✅ | OpenClaw via Tailscale MagicDNS (vps-cartorio/openclaw.tail2fe279.ts.net) |
| **v0.4.2** | 2026-06-23 14:25 | 1.2 | ✅ | Supabase 13/13 + Evolution instance + 4 endpoints + tabela atendimentos |
| **v0.4.1** | 2026-06-23 14:10 | 1.1 | ✅ | Backup diário OK + 11 WFs N8N + 5 endpoints novos |
| **v0.4.0** | 2026-06-23 11:00 | 1 | ✅ | API Protocolo (GET/POST) + LGPD Gate + PII scrub + 91% coverage |
| **v0.3.1** | 2026-06-23 10:42 | - | ✅ | Incident recovery (LiteLLM hack + DBs limpos) |
| **v0.3.0** | 2026-06-23 08:45 | 0.5+1 | ✅ | Infra verde + MCP server (combined_lifespan) |
| **v0.2.0** | 2026-06-22 | 0.5 | ✅ | Infra base deployada (Easypanel + Swarm + Traefik) |
| **v0.1.0** | 2026-06-22 | 0 | ✅ | Skeleton (FastAPI + SQLAlchemy + Alembic) |
| **v0.0.1** | 2026-06-19 | - | ✅ | Initial bootstrap (repo + .harness/ + 3 reins) |

**Detalhe completo**: `docs/CHANGELOG.md` (473 linhas, formato Conventional Commits + critérios de done).

---

## 🏗️ ARQUITETURA MACRO (1 slide)

```
                        ┌─────────────────────────────────────────┐
                        │   VPS 187.77.236.77 (Hostinger)         │
                        │   Tailscale: 100.99.172.84              │
                        │   12 containers Docker Swarm            │
                        └─────────────────────────────────────────┘
                                          │
        ┌──────────────┬──────────────────┼──────────────────┬──────────────┐
        │              │                  │                  │              │
        ▼              ▼                  ▼                  ▼              ▼
┌─────────────┐ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Evolution   │ │ N8N + Runner│  │ OpenClaw    │  │ Supabase    │  │ Chatwoot    │
│ API :8080   │ │ :5678       │  │ Gateway     │  │ :8000       │  │ :3000       │
│ WhatsApp    │ │ Workflows   │  │ :18789      │  │ 15 services │  │ CRM/Atend.  │
│             │ │ (11 ativos) │  │ Multi-canal │  │ 5 DBs       │  │ Humano      │
└──────┬──────┘ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │               │                │                │               │
       │               │  HTTP          │  HTTP          │  SQL           │
       │               ▼                ▼                ▼               │
       │       ┌─────────────────────────────────────────────┐           │
       │       │  API FastAPI (cartorio_api)                 │           │
       │       │  - 18 endpoints REST                        │           │
       │       │  - MCP server /mcp/mcp (FastMCP 3.x)       │           │
       │       │  - Swagger /docs (PT-BR)                    │           │
       │       │  - Audit log + PII scrub + LGPD gate        │◄──────────┘
       │       │  - LLM via OpenCode-Go (DeepSeek V4 Flash)  │
       │       └────────────────┬────────────────────────────┘
       │                        │
       │                        ▼
       │              ┌─────────────────┐
       │              │ Redis :6379/1001│
       │              │ (cache + fila)  │
       │              └─────────────────┘
       │
       ▼
  ┌────────────────────────┐
  │ WhatsApp Business API  │
  │ (cliente final)        │
  └────────────────────────┘
```

**Detalhe completo**: `docs/ARCHITECTURE.md` + `docs/COMMUNICATION_ARCHITECTURE.md`.

---

## 🧠 TIME (3 REINS + ORQUESTRADOR)

| Agent | Role | Quando spawnar | Limites |
|-------|------|----------------|---------|
| **Mavis (Pietra)** | Orquestrador | Eu mesmo sempre | NÃO escreve código de regra/WF/LGPD. Roteia + decide + reporta |
| **cartorio-dev** | Backend Python/FastAPI | Mudança em API, modelo, endpoint, SQLAlchemy, pytest | Cobertura ≥ 90%, mypy 0 errors, ruff limpo |
| **cartorio-n8n** | Workflows N8N + multi-canal | Mudança em WF, gateway OpenClaw, Evolution, deploy | Testa em staging, exporta JSON, valida creds |
| **cartorio-lgpd** | Compliance/LGPD | Mudança em `audit`, `pii`, retenção, consentimento, copy jurídica | BLOQUEIA merge se quebrar LGPD by design |

**Fluxo padrão**:
```
Gustavo (root) → Pietra (orquestra) → Rein (executa) → Rein (reporta) → Pietra (valida) → Gustavo (decide)
```

---

## 🔧 STACK

| Camada | Tech | Versão | Por quê |
|--------|------|--------|---------|
| API | FastAPI + Pydantic v2 + SQLAlchemy 2.x | 0.4.0 | Tipagem forte, async, OpenAPI auto |
| DB | MariaDB / Supabase Postgres | 10.11 / 15 | Relacional sólido + Supabase BaaS |
| Cache/Fila | Redis 7 + Bull (futuro) | 7.x | Velocidade + sessão WhatsApp |
| Workflows | N8N (self-hosted) | 2.x | Visual + auditável + extensível |
| Gateway | OpenClaw | 0.4.0 | Multi-canal messaging |
| WhatsApp | Evolution API | 2.x | Multi-device, webhooks, BAAS |
| CRM/Atend. | Chatwoot | 3.x | Open source, omnichannel |
| LLM | OpenCode-Go (DeepSeek V4 Flash) | API | Low-cost, compatível OpenAI |
| LLM Router | LiteLLM (futuro) | - | HA + fallback multi-provider |
| Front | (não existe ainda) | - | Só backend por enquanto |
| Deploy | Docker Swarm + Easypanel + Traefik | - | 1-click, HTTPS auto, Traefik routers |
| VPN | Tailscale | - | Zero-config, MagicDNS, segurança max |
| DNS | Cloudflare | - | Proxy, WAF, SSL/TLS 1.3 |

---

## 📊 KPIs (do ROADMAP)

| Sprint | KPI | Meta | Status |
|--------|-----|------|--------|
| Sprint 1 | Consultas emolumento/dia | 100 | ⏳ medindo |
| Sprint 1 | Erro de valor | 0 | ✅ 0 até agora |
| Sprint 1 | Handoff humano | 0% | ✅ 0% |
| Sprint 2 | Sugestões aceitas sem edição | 95% | ⏳ próximo |
| Sprint 3 | Protocolos criados via bot | 50% | ⏳ pós-30d shadow |
| Coverage | pytest --cov | ≥ 90% | ✅ 91.08% (v0.4.0) |
| LGPD | Audit log entries/dia | 100% das mutações | ✅ |

---

## 🚦 RADAR (sinal geral)

| Domínio | Sinal | Última verificação |
|---------|-------|---------------------|
| **API FastAPI** | 🟢 | 2026-06-23 13:50 |
| **MCP server** | 🟢 | 2026-06-23 13:50 |
| **OpenClaw health** | 🟢 | 2026-06-23 13:50 |
| **OpenClaw /v1/chat** | 🔴 | 2026-06-23 13:50 (404) |
| **N8N workflows** | 🟡 | 2026-06-23 13:48 (11 ativos, 5 duplicatas inativas) |
| **N8N credentials** | 🟢 | 2026-06-23 13:48 (4 creds) |
| **N8N Variables** | 🔴 | 2026-06-23 13:48 (feat:variables não licenciado) |
| **Supabase** | 🟢 | 2026-06-23 13:50 (15/15 services) |
| **Chatwoot** | 🟢 | 2026-06-23 13:50 |
| **Evolution API** | 🟢 | 2026-06-23 13:50 |
| **Tailscale VPN** | 🟢 | 2026-06-23 13:50 |
| **Tailscale subdomínios** | 🔴 | 2026-06-23 13:50 (000) |
| **Backup diário** | 🟢 | 2026-06-23 11:25 |
| **LGPD compliance** | 🟢 | 2026-06-23 (cartorio-lgpd audita contínuo) |
| **Testes pytest** | 🟢 | 2026-06-23 (91.08% coverage) |
| **Ripd v1.1** | 🟢 | 2026-06-23 |

**3 vermelhos** = ação imediata:
1. OpenClaw /v1/chat 404 — Gustavo precisa decidir (investigar ou esperar próxima release OpenClaw)
2. N8N Variables não licenciado — Gustavo precisa decidir (upgrade ou workaround $env permanente)
3. Tailscale subdomínios — cartorio-devops vai gerar cert + Traefik router

---

## 📋 PENDÊNCIAS CONHECIDAS (resumo executivo)

### P0 — Bloqueia produção
- (nenhuma crítica no momento)

### P1 — Hardening
- OpenClaw /v1/chat 404 (decisão Gustavo)
- Tailscale subdomínios (cartorio-devops)
- Chatwoot super_admin password (decisão Gustavo)
- Opencode-Go virar módulo dedicado (cartorio-dev)
- 5 WFs Monitor duplicatas (cartorio-n8n)
- WF #07 cred Evolution (cartorio-n8n)
- Re-export WFs pra JSON (cartorio-n8n)
- LGPD audit Opencode-Go + WFs NOVOS (cartorio-lgpd)
- RIPD v1.2 com Opencode-Go + N8N (cartorio-lgpd)

### P2 — Próximos sprints
- Chatwoot domínio (chatwoot.2notasudi.com.br CNAME)
- Cartorio API restart pra carregar MCP server novo
- Tailscale exit node pra Gustavo
- Evolution <-> N8N webhook integration real
- Chatwoot <-> N8N inbox integration real

### P3 — Backlog
- Prospecção cartórios (T2: 60 leads em 60d)
- LiteLLM HA (2 replicas, fallback)
- LLM local Llama 3.1 8B pra PII scrub
- Multi-canal (Telegram, Web, Email)
- gov.br/ICP-Brasil assinatura digital
- BI dashboard executivo
- App mobile nativo

**Detalhe completo**: `docs/PENDENCIAS_SUI_2026-06-23.md` (8 SUI) + `.harness/TASKS.md` (sprint tasks).

---

## 🔐 DECISÕES CEO (transcrição)

| Data | Decisão | Por quê |
|------|---------|---------|
| 2026-06-19 | Arquitetura HÍBRIDA (código + N8N + OpenClaw) | "Não pode errar" exige testes + audit |
| 2026-06-19 | LGPD by design (PII scrub 3 camadas + audit log HMAC) | Cartório lida com dado pessoal |
| 2026-06-19 | Sprint 1 SÓ consulta emolumento (read-only) | Validar com escrevente real antes de bot write |
| 2026-06-19 | MVP > plano perfeito | Ship rápido > debate |
| 2026-06-19 | Domínio público (*.2notasudi.com.br) + Tailscale VPN (admin) | Segurança + usabilidade |
| 2026-06-19 | Opencode-Go (DeepSeek V4 Flash) low-cost pra começar | Validar antes de subir tier (Claude Opus/GPT-5) |
| 2026-06-19 | **Prospecção MANUAL via Telegram (CEO dispara)**, NÃO bot | Sem opt-in de cartórios = spam + LGPD risk |
| 2026-06-19 | N8N workflows SEMPRE chamam API backend | Audit chain + LGPD by design (Postgres direto = bypass) |
| 2026-06-19 | Chatwoot: Gustavo cria super_admin via UI (não automatiza) | Rate-limit + decisão de produto |

---

## 📂 ESTRUTURA DE ARTEFATOS

```
/Users/gustavoalmeida/projetos/Cartorio/
├── backend/                        # FastAPI + SQLAlchemy + pytest
│   ├── app/                        # código fonte
│   │   ├── api/v1/router.py        # 18 endpoints REST
│   │   ├── core/                   # config, security, db
│   │   ├── models/                 # SQLAlchemy
│   │   ├── schemas/                # Pydantic
│   │   ├── services/               # regras de negócio
│   │   └── pii/                    # scrubber
│   ├── tests/                      # pytest (91% coverage)
│   ├── alembic/                    # migrations
│   ├── mcp_server.py               # FastMCP 3.x
│   ├── pyproject.toml
│   └── .env.example                # template (commit-friendly)
├── docs/                           # documentação viva
│   ├── CHANGELOG.md                # ⭐ histórico de versões
│   ├── ROADMAP.md                  # 12 semanas
│   ├── SUPER_PLAN.md               # visão macro
│   ├── ARCHITECTURE.md             # 1-slide arquitetura
│   ├── COMMUNICATION_ARCHITECTURE.md
│   ├── EVOLUTION_API_INTEGRATION.md
│   ├── ripd.md                     # Relatório Impacto Proteção Dados
│   ├── consent.md                  # termo consentimento
│   ├── privacy-policy.md
│   ├── PROSPECCAO_MERCADO.md       # ⭐ pesquisa + template
│   ├── PENDENCIAS_SUI_2026-06-23.md
│   ├── SMOKE_TEST_REPORT.md
│   ├── ENV_PRODUCTION.md
│   ├── VERSIONAMENTO_PROJETO.md    # ⭐ este arquivo
│   └── leads/                      # scripts prospecção
├── infra/                          # configurações deploy
│   ├── n8n-workflows/              # JSONs exportados
│   ├── backup/
│   └── supabase/
├── .harness/                       # time multi-agent
│   ├── TASKS.md                    # sprint tasks
│   ├── AGENTS.md                   # protocolo time
│   ├── STANDARDS.md                # padrões código
│   ├── agent.md                    # orquestrador
│   ├── memory/MEMORY.md            # memória compartilhada
│   └── reins/                      # 3 rein definitions
├── infra/backup/                   # backup scripts
├── Dockerfile
├── README.md
├── SESSION_SUMMARY_2026-06-23.md   # resumo última sessão
├── package.json
└── .env.example                    # template global
```

---

## 🎓 COMO USAR ESTE DOC

**Sou novo agent (Mavis cold start)**: Ler `VERSIONAMENTO_PROJETO.md` (este) → `CHANGELOG.md` (entender o que foi feito) → `.harness/AGENTS.md` (entender time) → começar.

**Sou agent do Mavis e vou trabalhar em sprint**: Ler `ROADMAP.md` (qual sprint) → `.harness/TASKS.md` (tasks específicas) → `docs/` relacionado (integração Evolution, LGPD, etc).

**Sou Gustavo e quero saber o que tá acontecendo**: Ler "ONDE ESTAMOS" + "RADAR" + "PENDÊNCIAS CONHECIDAS" + "DECISÕES CEO" (todas nesse doc, 5min de leitura).

**Memory agent (Mavis memory)**: Salvar index em `~/.mavis/agents/mavis/memory/MEMORY.md` referenciando este doc + `docs/CHANGELOG.md` (não duplicar).

Modified by Gustavo Almeida
