# Cartório 2notas — SUPER PLANO v2 (150 tasks)

**Atualizado**: 2026-06-25 08:14 BRT (briefing Gustavo turno 3 — "rodar o dia todo, 1-2 agents/vez, sem chave rotacionar, 100+ tasks de melhoria sem refazer")
**Orquestrador**: Pietra (Mavis, root session mvs_6663ee57a937460fb324e496cb5ac217)
**Squads**: cartorio-dev + cartorio-n8n + cartorio-lgpd + cartorio-zcode (docs) + cross
**Modo**: 1-2 agents max em paralelo, sequencial o resto. Sem mass-spawn. Sem rotação de chaves. Sem refazer — só melhorar.
**Gate global**: coverage >= 90%, ruff clean, mypy strict 0 errors, audit chain verificada.

## Status consolidado 08:14 BRT 25/06

### API Health (curl Mac, direto VPS)
- `api.2notasudi.com.br` → 200, 8/8 integrações online ✅
- `n8n / evo / chatwoot / supabase / openclaw / traefik` → NXDOMAIN (SUI 1.1 pendente Gustavo no Hostinger)
- VPS interna (Swarm): **13/13 containers UP** (api x3 healthy/starting, n8n + n8n-runner, chatwoot + chatwoot-sidekiq, evolution-api, openclaw-gateway, redis, easypanel, supabase x13)

### Containers Swarm estado
- `cartorio_api.1.973c307ddb70` HEALTHY 24min (reiniciei p/ sincronizar env)
- `cartorio_api.1.ff768a1a3822` + `1ed9fe6f59e0` health=starting 25-27s (subindo após restart)
- Todos os outros UP 5h-42h ✅

### Integrações API (/api/v1/health/integracoes)
- database 1ms, redis 2ms, n8n 10ms, openclaw 9ms, evolution 212ms, chatwoot 21ms, supabase 20ms (401 ok), opencode_go 397ms — **8/8 GREEN**

### Pendências SUI (só Gustavo resolve)
- 1.1 DNS Hostinger: n8n, evo, chatwoot, supabase, openclaw, traefik → 187.77.236.77
- 1.2 Credencial Evolution API no N8N UI
- 1.3 Agent Bot Chatwoot "Cartório Assistant"
- 1.4 Easypanel API key (decidido: NÃO rotacionar)
- 1.5 OpenClaw LLM key (contexto 131.1k → 1M; thinking adaptativo)
- 1.6 Decisão DNS typo `supbase` → `supabase`
- 1.7 QR scan WhatsApp Business instance `cartorio-2notas`

## Sprints do Plano v2

### Sprint 4 — Continuidade LGPD + DB hardening (D5-D10 → D13-D18)
- D13: Job retenção 5y/até-revogação (auto-delete audit >1825d, conversas >365d) — **EM ANDAMENTO**
- D14: DPA fornecedores (Evolution/N8N/Chatwoot/OpenClaw/Supabase/Render) — LGPD art. 33
- D15: IP truncation em logs (último octeto zero) — LGPD minimização
- D16: Audit ANPD relatório anual auto-gerado
- D17: Privacy Impact Assessment (RIPD) por feature nova
- D18: Direito ao esquecimento cascade DELETE cliente→conversa→protocolo→documento→emolumento

### Sprint 5 — SQUAD A13-A25 (backend hardening)
- A13 Dead man's switch audit cron parado >1h alerta Telegram
- A14 Backup DB 4x/dia pg_basebackup + WAL retenção 7d local + S3 mensal
- A15 Connection pool tuning pool=20 overflow=10 pre_ping
- A16 Query slow log >200ms + endpoint /admin/slow-queries
- A17 Materialized view mv_emolumento_ativo refresh diário
- A18 Trigger update_at automático em todas tabelas
- A19 Soft delete pattern global deleted_at + filtro query
- A20 Lock distribuído Redlock p/ migrations e seed
- A21 Cache Redis 24h emolumento com invalidação pub/sub
- A22 Cache warming cron 06:00 antes expediente
- A23 OpenAPI spec validada openapi-spec-validator no CI
- A24 Versionamento /api/v1 + /api/v2 alpha sunset 2027
- A25 RFC 7807 problem+json em todos 4xx/5xx

### Sprint 6 — SQUAD B6-B25 (N8N polish + WhatsApp integration)
- B6-B10 já em curso (error handler, retry, timeout, logs, métricas)
- B11 Alertas Telegram para falha WF GRUPO Pietra Squad
- B12 Test runner 28 WFs Playwright + workflow test kit
- B13-B15 Canned responses / macros / templates WhatsApp Meta
- B16-B20 Webhook signature / dedup / sessão / recovery / LGPD opt-out
- B21-B25 Variables N8N / Data Tables / audit log WF

### Sprint 7 — SQUAD D6-D25 (LGPD/DocOps expansion)
- D6-D12 já done (D8 PII sanitizer, D9 relatório ANPD, D11 consent service, D12 data export)
- D13-D18 novos (Sprint 4)
- D19-D25: DPA, RIPD,Privacy by Design checklist, treinamentos LGPD

### Sprint 8 — SQUAD E (LGPD Engineering — 15 tasks NOVAS)
- E01 LGPD consent granular por canal (whatsapp/telegram/web)
- E02 Data subject access request workflow automático
- E03 Portabilidade JSON + PDF format padrão LGPD art. 18 IV
- E04 Retenção configurável por tipo de documento (escritura 20y, certidão 5y, procuração 1y)
- E05 Anonimização irreversível após retenção (hash + k-anonymity)
- E06 Logs PII zero — substituir por hash + pseudônimo
- E07 Consent withdrawal propagação em <1min para Chatwoot + N8N + API
- E08 DPO dashboard acesso direto (relatórios, requests, incidentes)
- E09 Encarregado (DPO) sub-delegação com auditoria
- E10 Termo de uso versionado com aceite digital timestamp
- E11 Cookie banner LGPD-compliant opt-in/opt-out granular
- E12 Privacy policy auto-update diff visível para usuário
- E13 Transferência internacional (Supabase US) → cláusula contratual
- E14 Breach notification automation ANPD + titulares <72h
- E15 Auditoria externa anual automatizada (mock + checklist)

### Sprint 9 — SQUAD F (Testing & CI/CD — 15 tasks NOVAS)
- F01 Mutation testing mutmut com gate 80% mutants killed
- F02 Contract testing Pact p/ Evolution API + N8N
- F03 Load testing k6 1000 RPS baseline
- F04 Chaos engineering Chaos Mesh (kill api container test recovery)
- F05 E2E Playwright full flow: cliente→consulta→emolumento→recibo
- F06 Visual regression Percy/Chromatic p/ Chatwoot UI
- F07 Security test OWASP ZAP baseline scan
- F08 Performance budget Lighthouse CI <2.5s LCP
- F09 Dependency scanning Snyk/Trivy daily
- F10 Pre-commit hook multi-stage (ruff + mypy + pytest quick + bandit)
- F11 GitHub Actions matrix 3 Python versions 3.11/3.12/3.13
- F12 Render preview deployment auto per PR
- F13 Coverage trend report Codecov + Slack notification
- F14 Test data factory Faker BR (CPF/CNPJ/RG/MSK generators)
- F15 Flaky test quarantine + auto-retry 3x + report

### Sprint 10 — SQUAD G (Hardening Prod & SRE — 10 tasks NOVAS)
- G01 Grafana dashboard 12 panels (latência/error rate/CPU/RAM/disk)
- G02 Prometheus alert rules 25 (P0/P1/P2 com routing Telegram)
- G03 Distributed tracing Jaeger OTLP API + N8N + Supabase
- G04 Log aggregation Loki + Grafana com PII scrubber
- G05 Status page público status.2notasudi.com.br (Caddy)
- G06 Incident runbook 20 cenários (DB down, Redis down, N8N stuck, etc.)
- G07 Game day monthly — simular incidente real
- G08 Backup verification automático (restaurar em staging 1x/semana)
- G09 Disaster recovery drill quarterly
- G10 Cost monitoring diário OpenCode-Go USD/EUR/BRL budget alerts

### Sprint 11 — SQUAD H (Performance & Otimização — 10 tasks NOVAS)
- H01 Bundle analyzer backend (py-spy) + flamegraph CI
- H02 Database query plan analyzer EXPLAIN em todas queries lentas
- H03 Connection pool per worker pgbouncer transaction mode
- H04 Redis cluster 3 nodes sharding + replicas
- H05 CDN Cloudflare em assets estáticos + cache-control headers
- H06 Response compression gzip/brotli middleware
- H07 HTTP/2 + HTTP/3 enabled Traefik
- H08 Cache-Control ETag strong validator API
- H09 LLM response cache Redis 24h por hash prompt
- H10 Pre-warm pool idle connections keep-alive

### Sprint 12 — SQUAD I (UX/Dashboard/Browser AI — 10 tasks NOVAS)
- I01 Dashboard admin React 19 + shadcn/ui (clientes/protocolos/recebimentos)
- I02 Realtime updates WebSocket Supabase channels
- I03 Dark mode + accessibility WCAG AA
- I04 Mobile-first PWA installable offline-capable
- I05 Gráficos ApexCharts (receita por mês, top emolumentos, conversão)
- I06 Filtros avançados (período/status/cartório/tipo) + export CSV/PDF
- I07 Bulk operations (reenviar recibo, cancelar protocolo em lote)
- I08 Audit log viewer com diff chain visualizer
- I09 Browser AI agent (Playwright MCP) p/ UX testing automatizado
- I10 Notificações push Telegram in-app Web Push API

### Sprint 13 — SQUAD J (Integrações Jules/Linear/Render/Context7 — 15 tasks NOVAS)
- J01 Jules API configurado com Render MCP + Linear MCP + Context7 MCP
- J02 Jules background agent monitorando PR + auto-fix preview build
- J03 Linear API webhook sync Mavis/ZCode/Jules/Antigravity tasks
- J04 Linear projeto CAR-2NOTAS com 150 tasks mapeadas (esta plano)
- J05 Render auto-deploy on master push (já ON, F02 confirmar)
- J06 Render MCP serverless function p/ OpenClaw control plane
- J07 Context7 API doc lookup dinâmico p/ Evolution/N8N/Chatwoot/Supabase
- J08 Sequential Thinking MCP agent complexo task decompose
- J09 OpenCode Zen integração p/ tarefas simples (doc/test/format)
- J10 Qwen Coder 30B free tier p/ doc generation
- J11 Cross-platform sync state — Mavis session state JSON compartilhado
- J12 Worktree manager git worktree + Jules branch isolation
- J13 Jules commit policy MERGE master only + auto-clean branches
- J14 Cost dashboard cross-platform (Mavis/ZCode/Jules token USD/dia)
- J15 Jules prompt library 50 templates testados (cartorário)

## Dependências cross-squad

```
SUI 1.1-1.7 (Gustavo) ──┬─→ B6-B25 N8N polish (precisa DNS + credenciais)
                       ├─→ C6-C25 docs (precisa URL final)
                       └─→ E1-E15 LGPD (consentimento precisa Evolution UP)

A13-A25 backend ──┬─→ B25 audit WF (precisa audit_log estável)
                ├─→ D13 retenção job (precisa soft delete)
                └─→ E04 retenção por tipo (precisa schema migration)

D5-D18 LGPD ──┬─→ E01-E15 LGPD engineering (escopo contínuo)
            └─→ G06 runbook (precisa cenários reais)

F01-F15 CI/CD ──┬─→ A23 OpenAPI validate (gate CI)
              └─→ J05 Render preview (gate per PR)

G01-G10 SRE ──┬─→ B10 métricas WF (exporta p/ Prometheus)
            └─→ D9 relatório ANPD (dados precisam existir)

H01-H10 perf ──┬─→ F03 load test (baseline)
             └─→ G03 tracing (caminho otimizado)

I01-I10 UX ──┬─→ C01-C25 docs (admin precisa de manual)
           └─→ J11 sync state (config persistente)

J01-J15 integ ──┬─→ Mavis session list (precisa todos rodando)
              └─→ Linear ↔ Mavis bridge (tasks em ambos os lados)
```

## Modo de execução (do briefing Gustavo)

1. **1-2 agents/vez em paralelo** (não mais — economia de tokens)
2. **Sequencial o resto** (handoff explícito via `mavis communication send`)
3. **Loop engineer**: cada agent executa ciclo `analisar→testar→corrigir→melhorar→otimizar→documentar→comentar→salvar memória`
4. **Sem refazer** — sempre melhorar o que existe
5. **Sem parar** — continuar até amanhã cedo
6. **Report binário**: SUCCESS | FAIL — sem meia-truth
7. **Cron self-reminder** a cada 30min verificando progresso
8. **MEMORY canon atualizado** a cada task concluída

## Critérios de done globais

- [ ] Cada task: `pytest` verde, coverage >= 90%, ruff clean, mypy 0 errors
- [ ] Mudança em `audit` ou `pii`: review do `cartorio-lgpd` antes de merge
- [ ] Conventional Commits terminando com `Modified by Gustavo Almeida`
- [ ] MEMORY canon entry se lição cross-project
- [ ] Branch merge na master ou delete se não for útil
- [ ] API health check após deploy