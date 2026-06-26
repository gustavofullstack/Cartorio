# VERSIONAMENTO — Cartório AI OS

> **Índice rápido** pra qualquer agent pegar contexto em < 2min.
> Pra detalhes, ler: `docs/CHANGELOG.md` (granular) + `docs/ROADMAP.md` (12 semanas) + `docs/SUPER_PLAN.md` (visão macro).

---

## 🎯 ONDE ESTAMOS (snapshot 2026-06-26 20:00 BRT)

```
VERSÃO ATUAL:        v0.6.0
FASE:                Fase 3 — Multi-canal + Escala (concluído)
SPRINT ATUAL:        Hardening contínuo — Qualidade + Observabilidade + LGPD
PRÓXIMO SPRINT:      WhatsApp produção + Go-Live
RADAR:               🟢 8/8 GREEN (API, N8N, Evolution, Chatwoot, Redis, OpenClaw, Supabase, Easypanel)
```

### STATUS SNAPSHOT

- ✅ **API**: FastAPI v0.6.0 — 58+ endpoints REST, MCP server (164 tools), Swagger PT-BR
- ✅ **N8N**: 34 workflows ativos, 5 plugins, retry 3x, timeout config, correlation-id
- ✅ **Supabase**: 134 tabelas, 13 core, RLS ativo, pg_cron, webhooks, realtime
- ✅ **Redis**: v8.8.0, 1.7k keys, 3.1MB, PONG
- ✅ **OpenClaw**: Contexto 1M CONFIRMADO, Pietra Cartório, 7 skills, 5 providers, 9 fallback chain
- ✅ **Evolution API**: v2.3.7, TEST conectado (553497376057), produção aguardando QR
- ✅ **Chatwoot**: v4.12.1, Telegram inbox ativo, HITL configurado
- ✅ **GitHub**: Branch master, CI/CD ativo, 1543 testes, 90.18% coverage, 0 mypy, 0 ruff

### ISSUES CONHECIDOS

| Severidade | Issue | Status |
|-----------|-------|--------|
| 🔴 CRÍTICO | Evolution cartorio-2notas disconnected (401 desde 25/06) | **Só Gustavo (QR scan)** |
| 🔴 CRÍTICO | Supabase JWT secret = default (`your-super-secret-jwt-...`) | **Só Gustavo (rotação)** |
| 🔴 CRÍTICO | OpenCode API rate limit mensal atingido (429) — reset em ~10d | **Aguardando** |
| 🟡 HIGH | N8N Error Handler Global (WF #00) — $env bloqueado | **Agent-fixável** |
| 🟡 HIGH | API exit 137 (SIGKILL/OOM) — reinícios recentes | **Investigar** |
| 🟡 HIGH | UFW não instalado — Redis na porta 1001 exposto publicamente | **Agent-fixável** |
| 🟡 HIGH | Real API key em .env.example (comentário) | **Agent-fixável** |
| 🟡 MEDIUM | ROADMAP.md + VERSIONAMENTO_PROJETO.md desatualizados | ✅ **CORRIGIDO** |
| 🟡 MEDIUM | Alembic migration chain (down_revision mismatch) | ✅ **CORRIGIDO** |
| 🟡 MEDIUM | 16 stale remote branches (jules-*, fix-*, sentinel-*) | **Agent-fixável** |
| 🟢 LOW | 17 apt updates pendentes (Docker, containerd, apparmor) | **Agendar** |

---

## 📦 HISTÓRICO DE VERSÕES (resumo)

| Versão | Data | Sprint | Status | Resumo |
|--------|------|--------|--------|--------|
| **v0.6.0** | 2026-06-24 | 3 | ✅ | 58+ endpoints, A26 caching, 1543 testes, 90.18% coverage |
| **v0.5.4** | 2026-06-24 | 2.5 | ✅ | LGPD D18-D25, runbooks, brain API, Chatwoot script |
| **v0.5.0** | 2026-06-24 | 2 | ✅ | Alembic merge, Supabase completo, S01 Final |
| **v0.4.5** | 2026-06-23 | 1.3 | ✅ | 15 WFs N8N, 5 MCP servers (164 tools), backup |
| **v0.4.3** | 2026-06-23 | 1.2 | ✅ | OpenClaw via Tailscale, Evolution API instance |
| **v0.4.2** | 2026-06-23 | 1.1 | ✅ | Supabase 13/13, backup OK, 11 WFs N8N |
| **v0.4.0** | 2026-06-23 | 1 | ✅ | API Protocolo, LGPD Gate, PII scrub, 91% coverage |
| **v0.3.0** | 2026-06-23 | 0.5 | ✅ | Infra verde + MCP server |
| **v0.2.0** | 2026-06-22 | 0 | ✅ | Infra base deployada (Easypanel + Swarm + Traefik) |
| **v0.1.0** | 2026-06-22 | 0 | ✅ | Skeleton (FastAPI + SQLAlchemy + Alembic) |
| **v0.0.1** | 2026-06-19 | - | ✅ | Initial bootstrap (repo + .harness/) |

**Detalhe completo**: `docs/CHANGELOG.md` (~900 linhas, formato Conventional Commits + critérios de done).

---

## 🏗️ ARQUITETURA MACRO (1 slide)

```
                        ┌─────────────────────────────────────────────┐
                        │   VPS 187.77.236.77 (Hostinger)             │
                        │   Tailscale: 100.99.172.84                   │
                        │   28 containers (13 Swarm + 13 Supabase + 2) │
                        └─────────────────────────────────────────────┘
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Evolution  │ │ N8N + Run  │ │ OpenClaw   │ │ Supabase   │ │ Chatwoot   │
│ API :8080  │ │ :5678      │ │ Gateway    │ │ 13 services │ │ :3000      │
│ v2.3.7     │ │ 34 WFs     │ │ :18789     │ │ 134 tables  │ │ v4.12.1    │
│ WhatsApp   │ │ 5 plugins  │ │ 1M ctx     │ │ PG 15       │ │ CRM/HITL   │
└──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
       │              │              │              │              │
       │              │  HTTP        │  HTTP        │  SQL         │
       │              ▼              ▼              ▼              │
       │      ┌──────────────────────────────────────────────┐     │
       │      │  API FastAPI (cartorio_api) v0.6.0           │     │
       │      │  - 58+ endpoints REST                        │     │
       │      │  - MCP server (164 tools, 5 servers)        │     │
       │      │  - Swagger /docs (PT-BR)                     │     │
       │      │  - Audit log + PII scrub + LGPD gate         │◄────┘
       │      │  - LLM via OpenCode-Go (DeepSeek V4 Flash)   │
       │      └────────────────┬─────────────────────────────┘
       │                       │
       │                       ▼
       │             ┌─────────────────┐
       │             │ Redis :6379/1001│
       │             │ v8.8.0, 1.7k chs│
       │             └─────────────────┘
       │
       ▼
  ┌────────────────────────┐
  │ WhatsApp Business API  │
  │ (cliente final)        │
  │ ⏳ QR scan pendente    │
  └────────────────────────┘
```

---

## 📊 KPIs ATUAIS

| KPI | Meta | Atual | Status |
|-----|------|-------|--------|
| Testes passando | 1543+ | 1543 | ✅ |
| Coverage | ≥ 90% | 90.18% | ✅ |
| mypy errors | 0 | 0 | ✅ |
| ruff errors | 0 | 0 | ✅ |
| Serviços GREEN | 8/8 | 8/8 | ✅ |
| LGPD compliance | 100% | ~92% | 🟡 |
| Workflows N8N | 34 | 34 | ✅ |
| Endpoints API | 58+ | 60 | ✅ |

---

## 🧠 STACK

| Camada | Tech | Versão |
|--------|------|--------|
| API | FastAPI + Pydantic v2 + SQLAlchemy 2.x | v0.6.0 |
| DB | Supabase Postgres 15 | 15.x |
| Cache/Fila | Redis | 8.8.0 |
| Workflows | N8N (self-hosted) | 2.27.4 |
| Gateway | OpenClaw | Latest |
| WhatsApp | Evolution API | v2.3.7 |
| CRM/Atend. | Chatwoot | v4.12.1 |
| LLM | OpenCode-Go (DeepSeek V4 Flash) | 1M ctx |
| Deploy | Docker Swarm + Easypanel + Traefik | - |
| VPN | Tailscale | - |
| DNS | Cloudflare | - |

---

## 📂 ESTRUTURA DE ARTEFATOS

```
/Users/gustavoalmeida/projetos/Cartorio/
├── backend/                        # FastAPI v0.6.0
│   ├── app/                        # código fonte (284 source files)
│   │   ├── api/v1/router.py        # 58+ endpoints REST
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic V2
│   │   ├── services/               # 42 serviços
│   │   └── utils/                  # PII, utilidades
│   ├── tests/                      # 1543 testes, 90.18% coverage
│   ├── alembic/versions/           # 21 migrações (head 0016)
│   ├── mcp_server.py               # FastMCP 3.x
│   └── .env.example
├── docs/                           # 60+ documentos
├── infra/                          # N8N workflows, backup, supabase, chatwoot
├── .brain/                         # Memória do sistema
├── .harness/                       # Tasks, agents, planos
├── .secrets/                       # 15 .env files de serviço (gitignored)
└── .github/workflows/             # CI/CD (lint, test, docs-build)
```

---

## 🎓 COMO USAR ESTE DOC

**Sou novo agent (cold start)**: Ler `VERSIONAMENTO_PROJETO.md` (este) → `CHANGELOG.md` (entender o que foi feito) → `.harness/TASKS.md` → começar.

**Sou agente existente**: Verificar "ONDE ESTAMOS" + "ISSUES CONHECIDOS" + continuar do SESSION_SUMMARY mais recente.

**Sou Gustavo**: Ver "STATUS SNAPSHOT" + "ISSUES CONHECIDOS" — tudo em 2min de leitura.

---

*Modified by Gustavo Almeida | Atualizado 2026-06-26*
