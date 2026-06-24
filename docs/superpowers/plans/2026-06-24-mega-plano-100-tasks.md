# MEGA PLANO DE MELHORIA — 100 Tasks Cartorio Chatbot

> **Criado em**: 2026-06-24 09:30 BRT
> **Status**: Aguardando aprovacao do Gustavo
> **Premissa**: NAO refazer, apenas melhorar o que existe
> **Origem**: Auditoria local (382 testes, 92.22% coverage, ruff/mypy zero) + leitura de SESSION_SUMMARY_2026-06-23, ADRs 015-016, PENDENCIAS_SUI_2026-06-23, SUPER_PLANO_v0.6.0

## Como ler este plano

Cada task tem:
- **P?** = Prioridade (P0 = bloqueante, P1 = alta, P2 = media)
- **Area** = Backend (BE) | N8N | LGPD | DevOps (DO) | Documentacao (DC) | UX
- **Esforco** = S (<1h) | M (1-4h) | G (4-8h) | GG (>8h ou SUI)
- **Dependencias** = IDs de tasks que precisam estar prontas antes
- **Criterio done** = o que precisa estar VERIFICADO para considerar pronta

## Distribuicao

| Prioridade | Count | %  | Foco |
|---|---|---|---|
| P0 BLOQUEANTE | 10 | 10% | LGPD, prod-down, seguranca |
| P1 ALTA | 30 | 30% | Sprint 3-4 features, integracao |
| P2 MEDIA | 60 | 60% | Polish, DX, observabilidade, docs |

---

## P0 — BLOQUEANTES (resolver primeiro)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P0.1 | SUI | DNS `chatwoot.2notasudi.com.br` (B3 Easypanel UI) | S | — | Chatwoot acessivel via HTTPS com cert valida |
| P0.2 | SUI | N8N workflow #07 com credential Evolution (B4 N8N UI) | S | — | Workflow #07 ativo + recebe webhook Evolution |
| P0.3 | DO | Fix B1 Chatwoot restart loop (ADR-015) | M | P0.1 | Chatwoot uptime > 24h sem restart |
| P0.4 | DO | Fix B2 OpenClaw context overflow (ADR-016) | S | — | OpenClaw uptime > 7d, threshold 50 msgs + TTL 24h aplicado |
| P0.5 | BE | CNS 15/17dig check-digit em `pii.py` (LGPD art. 11) | S | — | Teste falha se CNS invalido; coverage 100% pii |
| P0.6 | BE | CNH 11dig check-digit em `pii.py` (LGPD art. 11) | S | — | Teste falha se CNH invalido |
| P0.7 | BE | Output PII scrub em `router.py:553` + `integrations.py:190` | M | P0.5,P0.6 | Teste que resposta Evolution com CPF eh mascarada |
| P0.8 | LGPD | Response shape `router.py:631-635` (expor pii_blocked, handoff) | S | — | Cliente recebe `{pii_blocked, handoff, ...}` |
| P0.9 | LGPD | Audit log `conversa.pii_blocked` (LGPD art. 37) | S | P0.8 | `audit_log` tem `pii_blocked` com request metadata |
| P0.10 | DO | Healthcheck `/health` robusto (todos os 6 servicos) | M | — | `/health` retorna 200 SÓ se todos os 6 servicos estao up |

---

## P1 — ALTAS (Sprint 3-4)

### Backend (10 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P1.BE.1 | BE | Encryption at-rest Postgres (L3 LGPD) | GG | — | Colunas PII encriptadas com pgcrypto |
| P1.BE.2 | BE | MCP server Evolution (Tarefa #26) | G | — | `mcp_evolution` tools: send_message, list_instances |
| P1.BE.3 | BE | MCP server Chatwoot (Tarefa #27) | G | — | `mcp_chatwoot` tools: pause_agent, resume_agent, list_conversations |
| P1.BE.4 | BE | MCP server Redis (Tarefa #28) | G | — | `mcp_redis` tools: get, set, publish |
| P1.BE.5 | BE | Endpoint `/admin/agent/pause` (HOLD de Agent via API) | M | P1.BE.3 | Gustavo pausa agente de uma conversa via API + audit log |
| P1.BE.6 | BE | Retry async com backoff (Evolution send) | M | — | 3 retries com 2^n backoff, dead letter queue |
| P1.BE.7 | BE | Dead letter queue (N8N ou Redis) | M | P1.BE.6 | Eventos com 3 falhas vao pra DLQ + alerta |
| P1.BE.8 | BE | `/metrics/prometheus` completa (gauge de DLQ, counter de retries) | S | P1.BE.7 | Prometheus coleta DLQ depth |
| P1.BE.9 | BE | OpenAPI spec exportada em `/openapi.json` validada | S | — | `swagger-cli validate /openapi.json` exit 0 |
| P1.BE.10 | BE | Endpoint `/cron/stale-detector` ja existe (Sprint 2), falta teste E2E | S | — | Teste E2E do cron em staging |

### N8N (8 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P1.N8N.1 | N8N | Workflow #24: Telegram bot de notificacoes | G | P0.2 | Gustavo recebe notificacao de P0/P1 events no Telegram |
| P1.N8N.2 | N8N | Workflow #25: Pesquisa de mercado cartorios | G | — | Job diario popula `leads/` com 5 cartorios/dia |
| P1.N8N.3 | N8N | Workflow #26: Backup diario Supabase | M | — | Backup automatico 03:00 + alerta se falha |
| P1.N8N.4 | N8N | Workflow #27: Sync audit log to Clickhouse/Supabase analytics | G | — | Audit log espelhado em `audit_analytics` table |
| P1.N8N.5 | N8N | Workflow #28: LGPD direito ao esquecimento (auto) | M | P1.BE.5 | Cliente pede esquecimento via chat → N8N processa + API executa |
| P1.N8N.6 | N8N | Test runner: rodar TODOS os 16 workflows com payload fake | G | P0.2 | Script `test_all_workflows.sh` exit 0 |
| P1.N8N.7 | N8N | Documentar 16 workflows (input, output, owner, failure mode) | M | P1.N8N.6 | `docs/N8N_WORKFLOWS.md` cobre todos os 16+ |
| P1.N8N.8 | N8N | Ativar UI para workflow #31 (CartorioBot Telegram test) | S | P0.2 | Gustavo ativa UI + bot responde em grupo Telegram |

### LGPD (6 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P1.LG.1 | LGPD | DPA Evolution API v1.0 (ja existe v0.5) | S | — | DPA assinado por Gustavo + Evolution |
| P1.LG.2 | LGPD | DPA MiniMax (LLM provider) | S | — | DPA assinado |
| P1.LG.3 | LGPD | DPA Opencode-Go | S | — | DPA assinado (ja existe template) |
| P1.LG.4 | LGPD | Direito ao esquecimento UI (cliente pede via chat) | M | P1.N8N.5 | Cliente conversa com bot → esqueci meu dado → audit log + soft delete |
| P1.LG.5 | LGPD | Consentimento explicito via WhatsApp (bot explica LGPD) | M | — | Primeira msg do cliente = consent prompt + grava `consent_at` |
| P1.LG.6 | LGPD | Retencao configuravel por tipo (D4 cartoraria) | M | P1.BE.1 | `retencao_config` table + job de purga respeitando config |

### DevOps (6 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P1.DO.1 | DO | GitHub Actions CI: ruff + mypy + pytest on PR | M | — | PR com erro de lint falha CI |
| P1.DO.2 | DO | GitHub Actions CD: build image + push to registry | M | P1.DO.1 | Tag `v*` dispara build + push |
| P1.DO.3 | DO | Easypanel auto-deploy from registry | M | P1.DO.2 | Push to main → Easypanel atualiza service |
| P1.DO.4 | DO | Backup automatico N8N workflows (diario, git ou S3) | M | — | `infra/n8n-workflows/` espelhado em `~/.mavis/backups/n8n/` |
| P1.DO.5 | DO | Grafana dashboard: requests, pii_blocks, DLQ, uptime | M | P1.BE.8 | Dashboard salvo em `infra/grafana/` |
| P1.DO.6 | DO | Alertmanager: P0 events → Telegram | S | P0.4,P1.N8N.1 | Gustavo recebe alerta em <5min se P0 |

---

## P2 — MEDIAS (60 tasks) — Polish, DX, Observabilidade, Docs

### Backend Polish (15 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P2.BE.1 | BE | Resolver 6 warnings pytest (httpx2, OpenTelemetry, AsyncMock) | S | — | pytest exit 0 com `-W error` |
| P2.BE.2 | BE | Coverage gate em 95% (subir de 90 → 95) | M | — | `pyproject.toml: --cov-fail-under=95` + 0 fail |
| P2.BE.3 | BE | Migrar SQLite (tests) → Postgres (docker-compose) | M | — | Testes rodam contra Postgres real |
| P2.BE.4 | BE | Performance test: 100 req/s em `/webhook/evolution` | M | — | `locust` confirma p99 < 500ms |
| P2.BE.5 | BE | Rate limit por IP alem de API key (defesa DDoS) | S | P1.BE.5 | 60 req/min por IP anonimo |
| P2.BE.6 | BE | Logging estruturado JSON (ja parcial) | M | — | Todos os logs em JSON com request_id, session_id, user_hash |
| P2.BE.7 | BE | Correlation ID cross-service (API → N8N → Evolution) | M | — | `X-Correlation-Id` propaga em todos os webhooks |
| P2.BE.8 | BE | Health check granular (`/health/db`, `/health/redis`, `/health/llm`) | S | — | Cada sub-health retorna 200 ou 503 com detalhes |
| P2.BE.9 | BE | Versioning API: `/api/v2` alem de `/api/v1` | G | — | v2 com breaking changes documentadas |
| P2.BE.10 | BE | Refatorar 5 endpoints grandes em router.py (split em arquivos) | M | — | router.py < 800 linhas |
| P2.BE.11 | BE | Pydantic v2 strict em todos os schemas (sem `extra=allow`) | S | — | `extra=forbid` em todos os request schemas |
| P2.BE.12 | BE | Type hints 100% em funcoes publicas (mypy strict em tudo) | M | — | `mypy --strict` exit 0 |
| P2.BE.13 | BE | Bench: `pii.scrub()` < 5ms p99 | S | — | Benchmark script confirma |
| P2.BE.14 | BE | Tracar OpenTelemetry em chamadas LLM (request + response time) | M | — | Spans em Jaeger/Tempo |
| P2.BE.15 | BE | Limpar 2 referencias mortas LiteLLM em docs | S | — | `grep -r litellm docs/` retorna 0 |

### N8N Polish (10 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P2.N8N.1 | N8N | Subflow reutilizavel: log + audit + retry | M | — | 1 subflow importado em 5+ workflows |
| P2.N8N.2 | N8N | Error workflow global (captura falhas de todos os workflows) | M | — | 1 workflow de error handling global |
| P2.N8N.3 | N8N | Versionar todos os 16+ workflows em git (ja parcial) | S | — | `git log infra/n8n-workflows/` mostra historico |
| P2.N8N.4 | N8N | Padronizar nomes: `cartorio-{acao}-{versao}` | S | — | 0 workflows com nome legado |
| P2.N8N.5 | N8N | Adicionar tag `production` em todos workflows ativos | S | — | Tag visible em N8N UI |
| P2.N8N.6 | N8N | N8N MCP server testado (HTTP transport) | M | P0.2 | `curl mcp-server/http` retorna tools list |
| P2.N8N.7 | N8N | N8N_QUEUE_HEALTH_CHECK workflow (5min) | S | — | Workflow ativo, alerta se fila > 100 |
| P2.N8N.8 | N8N | Mover credenciais de N8N pra Vault do Supabase | M | — | 0 credenciais em plain text em N8N |
| P2.N8N.9 | N8N | N8N_EXECUTIONs cleanup job (manter 30 dias) | S | — | Cron diario apaga executions > 30d |
| P2.N8N.10 | N8N | Backup completo N8N (workflows + creds + executions) | M | P2.DO.4 | Snapshot diario em S3 + restore testado |

### LGPD Polish (10 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P2.LG.1 | LGPD | Termo de consentimento revisado por juridico | M | — | Advogado assina termo v2.0 |
| P2.LG.2 | LGPD | Politica de privacidade PT-BR + EN | M | — | Publicada em `privacidade.2notasudi.com.br` |
| P2.LG.3 | LGPD | DPO designado oficialmente (CNPJ ou CPF no RIPD) | S | — | RIPD v2.1 com DPO nominal |
| P2.LG.4 | LGPD | Pen-test interno (LGPD art. 51) | GG | P1.BE.1 | Relatorio de pen-test + 0 P0/P1 abertos |
| P2.LG.5 | LGPD | Direito de acesso: cliente pede "todos os meus dados" | M | P1.N8N.5 | Endpoint ou fluxo que exporta JSON/PDF do cliente |
| P2.LG.6 | LGPD | Direito de portabilidade (LGPD art. 18 V) | M | P2.LG.5 | Export em formato estruturado (JSON/CSV) |
| P2.LG.7 | LGPD | RIPD v2.0 cobrindo todos os 10 principios | M | — | RIPD v2.0 com 10 secoes |
| P2.LG.8 | LGPD | Logs de acesso a dados sensiveis (quem viu o CPF do cliente X) | M | P0.9 | `audit_log.query_by_cliente()` retorna historico |
| P2.LG.9 | LGPD | Encriptar logs de PII em repouso (ja feito com hash chain, falta encryption) | M | P1.BE.1 | Logs encriptados com AES-256 |
| P2.LG.10 | LGPD | Revisao trimestral de DPA (todos os 4 providers) | S | — | Checklist + data da proxima revisao |

### Documentacao (15 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P2.DC.1 | DC | Baixar doc oficial Evolution API v2.x completa | M | — | `docs/EVOLUTION_API.md` com 50+ endpoints |
| P2.DC.2 | DC | Baixar doc oficial N8N 1.x completa (nodes, expressions) | M | — | `docs/N8N_REFERENCE.md` com 100+ nodes |
| P2.DC.3 | DC | Baixar doc oficial Chatwoot 3.x (API + agent bot) | M | — | `docs/CHATWOOT.md` com 80+ endpoints |
| P2.DC.4 | DC | Baixar doc oficial Supabase (Auth, Storage, Realtime, Edge Functions) | M | — | `docs/SUPABASE.md` com 100+ funcoes |
| P2.DC.5 | DC | Baixar doc oficial Redis 7.x (Streams, Pub/Sub, Cluster) | M | — | `docs/REDIS.md` com 50+ comandos |
| P2.DC.6 | DC | API doc completa: cada endpoint com curl exemplo + response | G | — | `docs/API.md` com 50+ endpoints documentados |
| P2.DC.7 | DC | Diagramas de arquitetura (C4 model) | M | — | 4 diagramas C4 em `docs/architecture/` |
| P2.DC.8 | DC | Onboarding para novo dev (10 passos em <2h) | M | — | `docs/ONBOARDING.md` |
| P2.DC.9 | DC | Troubleshooting FAQ (20 problemas comuns) | S | — | `docs/FAQ.md` |
| P2.DC.10 | DC | Diagrama de fluxo de dados (PII input → scrub → LLM → output → audit) | S | — | 1 mermaid diagram em `docs/DATA_FLOW.md` |
| P2.DC.11 | DC | Runbook completo: 10 cenarios de incidente | M | — | `docs/RUNBOOK.md` com 10 cenarios + resolucao |
| P2.DC.12 | DC | Postman collection publica (ja existe parcial) | S | — | `docs/postman_collection.json` v2.0 |
| P2.DC.13 | DC | ADRs: 020 (N8N MCP), 021 (pre-deploy validation), 022 (encryption at-rest) | S | — | 3 ADRs novos em `docs/adr/` |
| P2.DC.14 | DC | Changelog v0.6.0 (consolidar Sprint 3) | S | — | `CHANGELOG.md` com 20+ entregas |
| P2.DC.15 | DC | Video walkthrough (5min) do sistema funcionando | G | — | Video publicado (Loom/YouTube) |

### Memória & DX (10 tasks)

| ID | Area | Titulo | Esf | Dep | Criterio done |
|---|---|---|---|---|---|
| P2.MX.1 | MX | `.harness/memory/MEMORY.md` consolidado (1 arquivo < 2000 linhas) | M | — | Licoes duplicadas mergeadas, referencias cruzadas |
| P2.MX.2 | MX | `.harness/AGENTS.md` para CADA rein (dev, n8n, lgpd) | M | — | 3 AGENTS.md especificos |
| P2.MX.3 | MX | `.harness/TASKS.md` priorizado (P0/P1/P2 visivel) | S | — | Tasks com campo `priority` |
| P2.MX.4 | MX | Scripts uteis: `scripts/test-all.sh`, `scripts/deploy.sh` | S | — | 2 scripts em `scripts/` |
| P2.MX.5 | MX | Pre-commit hook: ruff + mypy + pytest rapido | S | P2.DC.1 | `pre-commit install` ativa gate |
| P2.MX.6 | MX | Makefile com alvos: `make test`, `make lint`, `make deploy` | S | — | `make help` lista 10+ alvos |
| P2.MX.7 | MX | Editor config (`.editorconfig`) | S | — | 1 arquivo cobrindo 4 linguagens |
| P2.MX.8 | MX | Template de PR (`.github/pull_request_template.md`) | S | — | Template com checklist de LGPD |
| P2.MX.9 | MX | Conventional commits enforced (commitlint) | S | — | Commit fora do padrao falha |
| P2.MX.10 | MX | ADRs index em `docs/adr/README.md` | S | — | Lista cronologica + tags |

---

## Resumo de esforço

| Bucket | Tasks | Esforco total estimado |
|---|---|---|
| P0 BLOQUEANTE | 10 | ~30h (4 SUI + 6 tecnico) |
| P1 ALTA | 30 | ~150h (3 sprints de 50h) |
| P2 MEDIA | 60 | ~120h (1-2 sprints) |
| **TOTAL** | **100** | **~300h** = ~6 sprints (12 semanas) |

## Recomendacao de execucao (sequencial, nao paralelo)

1. **Esta semana (P0)**: P0.1 + P0.2 (SUI Gustavo, 15min) → P0.4 → P0.5 + P0.6 → P0.7 → P0.8 + P0.9
2. **Proxima semana (P1.DO)**: P1.DO.1 + P1.DO.2 + P1.DO.6 → P0.3 (com rede ok) → P0.10
3. **Sprint 3 (P1.BE)**: P1.BE.1 → P1.BE.2 + P1.BE.3 + P1.BE.4 (MCPs) → P1.BE.5
4. **Sprint 4 (P1.N8N)**: P1.N8N.1 + P1.N8N.8 → P1.N8N.6 + P1.N8N.7
5. **Sprint 5-6 (P1.LG + P2)**: P1.LG.4 + P1.LG.5 + P2.BE.* (polish)

## Riscos & bloqueios conhecidos

- **SUI Gustavo**: 4 tasks P0 (P0.1, P0.2, P0.3, P0.4) dependem de acesso UI/SSH. **NAO posso fazer remotamente** sem MCPs configurados.
- **MCPs**: 3 tasks P1 (P1.BE.2/3/4) so fazem sentido DEPOIS de MCPs configurados em `.zcode/mcp-servers/`.
- **LGPD legal**: 2 tasks (P2.LG.1, P2.LG.4) exigem terceiro (advogado, pen-tester).
- **Testes E2E**: 3 tasks (P1.N8N.6, P1.BE.10, P2.BE.4) exigem staging environment com dados reais.

## Como este plano foi gerado

- Leitura de `SESSION_SUMMARY_2026-06-23.md` (Sprint 2 fechado, 5 SUI pendentes)
- Leitura de `PENDENCIAS_SUI_2026-06-23.md` (lista priorizada)
- Leitura de ADRs 015, 016 (Bugs B1, B2 documentados)
- Leitura de `SUPER_PLANO_v0.6.0.md` (visao macro)
- **Auditoria VERIFICADA** desta sessao: 382 testes, ruff 0, mypy 0, 6 warnings

## Modificado por

Modified by ZCode/Mavis (sessao 2026-06-24 09:30 BRT)
