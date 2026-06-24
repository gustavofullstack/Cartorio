# ROADMAP 100 MELHORIAS — Cartório 2notas (Sprint 4-7)

> Gerado por Pietra/Mavis 2026-06-24 após briefing Gustavo 14:13 BRT. **Princípio: NADA DE REFAZER, APENAS MELHORAR O QUE JÁ TEMOS**. Complementa o E6 (100 tasks integração full) que está em `.harness/TASKS.md`. Este aqui é a **segunda camada** de 100 melhorias incrementais — squads paralelos de até 25 tasks cada, 1-2 agents simultâneos MÁXIMO.

**Owner global**: Mavis (orquestrador)
**Squad owners**: cartorio-dev (BE), cartorio-n8n (WF), cartorio-lgpd (LGPD), cartorio-zcode (cross/integrador)
**Modo execução**: 1-2 agents paralelos, sequencial o resto
**Critério de done por task**: tests verde + coverage ≥90% (BE) ou WF test runner 100% (N8N) ou DPA assinado (LGPD)
**Comunicação final**: report formato padrão `[WORK] task=<id>, files=N, pytest=N passed, coverage=X%, commit=<hash>, push=ok`

---

## SQUAD A — API + DB HARDENING (cartorio-dev) — 25 tasks

### Camada observabilidade + audit
- [ ] **A1** Audit log em 100% das mutações (request_id + ip_trunc + user_agent + timestamp) — FALTA 5 endpoints
- [ ] **A2** Prometheus metrics: counter `pii_blocked_total`, histogram `scrub_latency_ms`, gauge `dlq_depth`
- [ ] **A3** OpenTelemetry tracing: span por request + span por LLM call + span por DB query
- [ ] **A4** Sentry error tracking com scrubber PII pré-envio
- [ ] **A5** Health check `/health/live` (liveness, sem deps) + `/health/ready` (readiness, com deps)

### Camada segurança
- [ ] **A6** Idempotency-Key header em todos POST com Redis SETNX TTL 24h
- [ ] **A7** Rate limit 60 req/min/IP Redis sliding window (já existe rudimentar, falta sliding)
- [ ] **A8** HMAC signature validation em todos webhooks (X-Signature header, AUDIT_HMAC_KEY)
- [ ] **A9** Encryption at-rest: pgcrypto + chave rotacionada (LGPD L3)
- [ ] **A10** Constraint check CPF/CNPJ no DB (CHECK regex + CHECK dígito verificador)
- [ ] **A11** Mask CPF/CNPJ em logs (substituir regex `[\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2}` por `***.***.***-**`)

### Camada resiliência
- [ ] **A12** DLQ com retry policy (3x exp backoff: 1min, 5min, 15min) + endpoint admin
- [ ] **A13** Dead man's switch: cron notifica se audit_log parado > 1h
- [ ] **A14** Backup automático DB 4x/dia (pg_basebackup + WAL archiving) com retenção 7d local + S3 mensal
- [ ] **A15** Connection pool tuning: pool_size=20, max_overflow=10, pool_pre_ping=True
- [ ] **A16** Query slow log: log automático de queries > 200ms + endpoint `/admin/slow-queries`

### Camada dados
- [ ] **A17** Materialized view `mv_emolumento_ativo` (refresh diário) com índice em `tipo_documento`
- [ ] **A18** Trigger `update_at` automático em todas tabelas
- [ ] **A19** Soft delete pattern global (`deleted_at TIMESTAMPTZ NULL`) + filtro automático query
- [ ] **A20** Lock distribuído via Redlock (sync entre API replicas) p/ migrations e seed inicial
- [ ] **A21** Cache Redis 24h emolumento com invalidation via pub/sub
- [ ] **A22** Cache warming: cron 06:00 popula cache antes do expediente

### Camada API surface
- [ ] **A23** OpenAPI spec validada via `openapi-spec-validator` no CI
- [ ] **A24** Versionamento de endpoint: `/api/v1` + `/api/v2` (alpha, sunset 2027)
- [ ] **A25** Documentação de erro estruturada (RFC 7807 problem+json) em todos 4xx/5xx

---

## SQUAD B — N8N WORKFLOWS POLISH (cartorio-n8n) — 25 tasks

### Documentação
- [ ] **B1** Documentar todos 28+ workflows em `infra/n8n-workflows/README.md` (1 WF = 1 seção com: trigger, input, output, error handling, SLO)
- [ ] **B2** Diagrama visual por WF (mermaid em MD) — facilita entendimento
- [ ] **B3** Versionamento WF em CHANGELOG (WF #1 v1 → v2 → v3 com diff)
- [ ] **B4** Backup WF export diário (cron 02:00) para `/var/backups/n8n-workflows/`
- [ ] **B5** Migration guide WF v1→v2 (cliente upgrade path)

### Resiliência WF
- [ ] **B6** Error handler global em todos WFs (Error Workflow trigger node)
- [ ] **B7** Retry policy em todos nodes HTTP (3x, exp backoff)
- [ ] **B8** Timeout 5s em todos HTTP requests (evitar hang)
- [ ] **B9** Logs estruturados JSON (correlation_id em todos nodes)
- [ ] **B10** Métricas Prometheus por WF (count executions, latency p50/p95/p99, error rate)
- [ ] **B11** Alertas Telegram para falha WF (template GRUPO Pietra Squad)
- [ ] **B12** Test runner todos 28 WFs (Playwright + workflow test kit)

### Chatwoot integration
- [ ] **B13** Canned responses Chatwoot (50+ templates jurídicos: certidão, procuração, escritura, etc)
- [ ] **B14** Macros handoff humano → escrevente (10 macros: identificar, transferir, resumir, etc)
- [ ] **B15** Templates WhatsApp aprovados Meta (10 templates: boas-vindas LGPD, handoff, follow-up, NPS, etc)
- [ ] **B16** Webhook signature validation em todos WFs que recebem webhook externo

### Sessão + estado
- [ ] **B17** Deduplicação msg WhatsApp (Redis SETNX com hash msg_id, TTL 24h)
- [ ] **B18** Sessão 24h TTL Redis com auto-refresh on msg
- [ ] **B19** Session recovery pós-crash (last 10 mensagens no DB, rehydration automática)
- [ ] **B20** LGPD opt-out keyword `PARAR`/`SAIR` → DELETE cliente cascade + audit log

### N8N variables + Data Tables
- [ ] **B21** Variables N8N (workaround $env): `cartorio.api_url`, `cartorio.api_key`, `chatwoot.bot_token`
- [ ] **B22** Data Table `cartorio-sessions` (chave=session_id, valor=JSON {phone, customer_id, last_msg_at, context, consent})
- [ ] **B23** Data Table `cartorio-leads` (chave=cartorio_id, valor=JSON {nome, status, ultimo_contato, opt_out})
- [ ] **B24** Data Table `cartorio-messages-cache` (chave=msg_hash, valor=JSON {content, intent, response}) TTL 7d
- [ ] **B25** Audit log todo WF (entrada + saída + erro em audit_log API)

---

## SQUAD C — OBSERVABILIDADE + DOCS (cartorio-zcode cross) — 25 tasks

### Documentação código
- [ ] **C1** README.md raiz completo (badges, quickstart, arquitetura, contrib)
- [ ] **C2** ARCHITECTURE.md diagramas C4 (Context, Container, Component, Code) + ADRs linkados
- [ ] **C3** API.md render OpenAPI (auto-gerado do FastAPI) + exemplos curl/Postman
- [ ] **C4** DB.md schema diagram (sql2diagram ou dbdiagram.io) com explicação de cada tabela
- [ ] **C5** DEPLOY.md Easypanel passo-a-passo (build, env, secret, port, health check)

### Documentação operacional
- [ ] **C6** RUNBOOK.md (restart container, restore backup, rotate secret, escalate incidente)
- [ ] **C7** LGPD.md compliance checklist (15 itens ANPD readiness)
- [ ] **C8** SECURITY.md threat model (STRIDE por componente)
- [ ] **C9** TESTING.md estratégia (unit, integration, e2e, load, pen-test)
- [ ] **C10** CONTRIBUTING.md padrão PR + Conventional Commits

### ADRs + changelogs
- [ ] **C11** ADRs 11-20 (audit chain, PII 3 camadas, HITL, hash chain, MFA, rate limit, etc)
- [ ] **C12** CHANGELOG.md completo (releases v0.1 a v0.6+)
- [ ] **C13** Postman collection v2 (todos endpoints + exemplos)
- [ ] **C14** Insomnia collection (alternativa)
- [ ] **C15** Bruno collection (alternativa open-source)

### Stack documentation download
- [ ] **C16** Documentação Evolution API v2.3.7 (oficial + community) em `docs/stack/evolution.md`
- [ ] **C17** Documentação N8N 1.x (oficial + self-hosted) em `docs/stack/n8n.md`
- [ ] **C18** Documentação Chatwoot 3.x (oficial + self-hosted) em `docs/stack/chatwoot.md`
- [ ] **C19** Documentação Supabase self-hosted (oficial + Easypanel) em `docs/stack/supabase.md`
- [ ] **C20** Documentação Redis 8.x (oficial + comandos úteis) em `docs/stack/redis.md`

### Observabilidade avançada
- [ ] **C21** Grafana dashboards (4): API health, N8N executions, DB queries, audit chain integrity
- [ ] **C22** Prometheus alerts (10 regras P0/P1/P2 com Telegram routing)
- [ ] **C23** Loki logs agregados por service (cartorio-api, cartorio-n8n, cartorio-evo, etc)
- [ ] **C24** Uptime Kuma externa (https://status.2notasudi.com.br) com monitor 5min
- [ ] **C25** Status page pública (https://status.2notasudi.com.br) — 90d uptime, incidents, scheduled maintenance

---

## SQUAD D — LGPD + COMPLIANCE AVANÇADO (cartorio-lgpd) — 25 tasks

### DPAs + contratos
- [ ] **D1** DPA MiniMax assinado (LLM provider)
- [ ] **D2** DPA Evolution API assinado
- [ ] **D3** DPA Opencode-Go assinado
- [ ] **D4** DPA Cloudflare assinado
- [ ] **D5** DPA Hostinger assinado (VPS hosting)

### Direitos do titular (LGPD art. 18)
- [ ] **D6** Direito de acesso (GET /cliente/{id}/historico) — já existe WIP, finalizar
- [ ] **D7** Direito de correção (PATCH /cliente/{id} com audit log)
- [ ] **D8** Direito de anonimização (POST /cliente/{id}/anonimizar)
- [ ] **D9** Direito de portabilidade (GET /cliente/{id}/export JSON + CSV + PDF)
- [ ] **D10** Direito de revogação (DELETE /cliente/{id} cascade) — já existe, refinar
- [ ] **D11** Direito de oposição (POST /cliente/{id}/opor) — parar tratamento
- [ ] **D12** Direito de não-automação (POST /cliente/{id}/opt-out-bot) — só humano

### Operacional LGPD
- [ ] **D13** Logs de acesso LGPD art. 37 (request_id + IP truncado /24 + user_agent + timestamp)
- [ ] **D14** Retenção configurável por tipo (cliente COM protocolo 5y, SEM protocolo até-revogação, conversa 2y, audit 5y)
- [ ] **D15** Encriptação at-rest (pgcrypto) + in-transit (TLS 1.3 obrigatório) — alinhado com A9
- [ ] **D16** Pseudonimização em analytics (cliente_id_hash em vez de CPF)
- [ ] **D17** Teste vazamento PII automatizado (CI roda suite 50+ tentativas, falha se vazar)

### Auditoria + treinamento
- [ ] **D18** Pen-test OWASP top 10 (Burp Suite + Zap, baseline anual)
- [ ] **D19** Auditoria ANPD readiness checklist (15 itens)
- [ ] **D20** Treinamento equipe LGPD (cartilha + quiz + certificado)
- [ ] **D21** Simulado incidente vazamento (tabletop exercise 2h com equipe)
- [ ] **D22** Plano resposta ANPD (comunicação 72h, mitigação, relatório)
- [ ] **D23** Relatório impacto anual (RIPD refresh + métricas)
- [ ] **D24** DPO designado + contato publicado no site/chat (canal direto)
- [ ] **D25** Política privacidade site institucional (página `/privacidade` linked do footer)

---

## Métricas globais (KPI do roadmap)

- **Sprint 4 (sem 1-2)**: 25 tasks A1-A25 + B1-B5 + C1-C5 = 35 tasks (BE + N8N + Doc)
- **Sprint 5 (sem 3-4)**: 25 tasks B6-B15 + C6-C15 = 25 tasks (N8N polish + Doc)
- **Sprint 6 (sem 5-6)**: 25 tasks C16-C25 + D1-D5 = 15 tasks (Stack docs + DPAs)
- **Sprint 7 (sem 7-8)**: 25 tasks D6-D25 = 20 tasks (Direitos titular + auditoria)
- **Total**: 100 melhorias incrementais (s/ refazer nada)

## Modo de execução

- **2 squads paralelos MÁXIMO**: ideal (BE + LGPD) ou (N8N + Doc)
- **1 squad sequencial** o resto
- **Cron morning-brief 07:30** resume status dos 4 squads
- **Cron weekly-summary Sunday 23:00** fecha sprint e atualiza `.harness/TASKS.md`

Modified by Gustavo Almeida
