# Cartório 2º Notas — PLANO 100 TASKS LOOP 2026-06-25

**Status global agora (2026-06-25 ~08:30 BRT)**:
- Gates backend: mypy 0 ✅ / ruff 0 ✅ / pytest 920 passed ✅
- OpenClaw: live, 1M context + thinking adaptive + 7 skills
- Telegram bot: OK (3 updates pendentes no webhook)
- 8/8 integrações GREEN em `/api/v1/health/integracoes`
- **Supabase: 0 tabelas (PGRST205) — BLOCKER P0**

## Prioridade de execução (1-2 agents max paralelo, sequencial o resto)

### 🔴 SQUAD S0 — SUPABASE FOUNDATION (10 tasks, P0-CRITICAL, BLOQUEIA 70%)
> Supabase é o banco central mas tem 0 tabelas. Tudo que faz query falha.

- S01 Schema completo (clientes, protocolos, atendimentos, documentos, emolumentos, audit_log, webhook_events, outbox_messages, lgpd_consents, lgpd_audit_anpd)
- S02 RLS policies (4 roles)
- S03 pg_cron jobs (audit_verify, dlq_retry, cache_warm, snapshot)
- S04 Database webhooks (outbox INSERT → N8N)
- S05 GraphQL via PostgREST
- S06 Storage buckets (3 buckets)
- S07 Realtime channels (3 channels)
- S08 Vault secrets (11 secrets)
- S09 Migrations Alembic setup
- S10 pgAudit + log_statement=all

### 🟡 SQUAD A — API+DB HARDENING (13 tasks, 5/13 done)
- A18 trigger update_at global
- A19 soft delete deleted_at + filter
- A20 Redlock distribuido
- A21 cache Redis 24h emolumento + pub/sub
- A22 cache warming cron 06:00
- A23 OpenAPI spec validator CI
- A24 /api/v1 + /api/v2 alpha
- A25 RFC 7807 problem+json

### 🟡 SQUAD B — N8N POLISH (10 tasks, 2/10 done)
- B08 timeout 5s HTTP
- B09 logs JSON correlation_id
- B10 metrics Prometheus por WF
- B11 alertas Telegram GRUPO Pietra
- B12 test runner 28 WFs Playwright
- B13 canned responses 50+
- B14 macros handoff 10
- B15 templates WhatsApp Meta 10

### 🟡 SQUAD C — DOCS RAIZ (25 tasks, 5/25 done)
- C6-C25 ops+audit+stack docs (Evolution, N8N, Chatwoot, Supabase, Redis, Jules, Render, Linear)

### 🟡 SQUAD D — LGPD (25 tasks, 12/25 done)
- D13 anonimização hash reversível p/ analytics
- D14 direito esquecimento cascade
- D15 portabilidade automatica zip+upload S3
- D16 base legal por tipo dado (consentimento/contrato/legítimo interesse)
- D17 RIPD (Relatório Impacto Proteção Dados) template
- D18 data breach notification (ANPD 72h)
- D19 consent banner versão LGPD 2026
- D20 DPO dashboard (métricas: consents, exports, queixas)
- D21 privacy by design checklist (revisão 9 itens)
- D22 training interno (5 vídeos LGPD)
- D23 site privacy policy v2
- D24 DPO contato publicado
- D25 auditoria ANPD anual (relatório gerado D9)

### 🟡 SQUAD E — OPENCLAW AGENT (8 tasks, 1/8 done)
- E2 thinking sempre ativo
- E3 skills registry auto-discovery
- E4 agent tools (api/n8n/supabase/redis/chatwoot/evolution)
- E5 agent config direto/curto/sério
- E6 testes E2E Telegram↔API↔N8N↔OpenClaw
- E7 métricas agent
- E8 failover chain opencode_go→openclaw→openrouter

### 🟢 SQUAD H — CHATWOOT CRM (8 tasks, 0/8)
- H1 Evolution API inbox
- H2 custom attributes (cpf_cnpj_hash, etc)
- H3 handoff macros 10
- H4 canned responses 50
- H5 labels
- H6 reports 5
- H7 automations
- H8 bot handoff 1-click

### 🟢 SQUAD J — OBSERVABILITY+CI/CD (10 tasks, 0/10)
- J1 Linear API: 100 tasks auto
- J2 Linear dashboard
- J3 Render API: services+autodeploy
- J4 Render: health checks custom
- J5 Jules API: sessions 5/dia
- J6 Jules: review+merge
- J7 GitHub Actions ci.yml
- J8 GitHub Actions cd.yml
- J9 Sentry SDK
- J10 OpenTelemetry collector

### 🟢 SQUAD DOCS — DOWNLOAD (5 tasks, 0/5)
- DOC1 Evolution API 2.3.7
- DOC2 N8N 1.94.x
- DOC3 Chatwoot 3.x
- DOC4 Supabase self-hosted
- DOC5 Redis 7.x

### 🟢 SQUAD BRAIN — LOCAL+PROD (8 tasks, 0/8)
- BRAIN1 /Users/gustavoalmeida/projetos/Cartorio/.brain/
- BRAIN2 /var/lib/docker/volumes/cartorio_brain/_data/ VPS
- BRAIN3 sync bidirecional rsync+ssh hourly
- BRAIN4 schema: tasks/plans/memory/lessons/agents
- BRAIN5 index.md auto-gera
- BRAIN6 /api/v1/brain/ endpoints
- BRAIN7 session memory auto-append
- BRAIN8 compact loop-state.json (1 página)

## Cronograma (5 dias, 1-2 agents max)

| Dia | Squad 1 (sempre) | Squad 2 (paralelo se houver) |
|---|---|---|
| 1 | S0 (S01-S05) schema+RLS+webhooks+graphql | A (A18-A22) |
| 2 | S0 (S06-S10) storage+realtime+vault+migrations | E (E2-E5) |
| 3 | H (H1-H5) chatwoot | D (D13-D17) |
| 4 | J (J1-J5) Linear+Render+Jules | BRAIN (BRAIN1-BRAIN5) |
| 5 | DOCS (DOC1-DOC5) + D (D18-D25) + BRAIN6-8 | E2E final |

## Regras
- 1-2 agents max paralelo
- Cada task = 1 commit (Conventional Commits)
- Push ao final de cada squad
- Atualizar MEMORY.md a cada sprint
- Atualizar plan-100-loop-2026-06-25.json após cada task

## Modo de operação
- SEMPRE que iniciar agent, passar:
  - plan-100-loop-2026-06-25.json (compact)
  - task específica do squad
  - tools ativas: Read, Edit, Write, Bash, Grep, Glob
  - skills: superpowers + verification-before-completion + TDD
- SEMPRE verificar gates após cada agent (mypy 0, ruff 0, pytest 920+)
- SEMPRE atualizar MEMORY.md com lições aprendidas
- NUNCA rotacionar chaves, NUNCA deletar, NUNCA criar worktree
