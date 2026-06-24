# Cartório 2notas — Roadmap 100 Tasks de Melhoria

**Atualizado**: 2026-06-24 12:05 BRT (briefing Gustavo turno 2)
**Orquestrador**: Pietra (Mavis, mvs_410a1b1266d64830b9dfa31973fdd9fe)
**Squad**: cartorio-dev + cartorio-n8n + cartorio-lgpd + cross-review obrigatório em `audit` / `pii` / `consentimento` / `retenção`
**Modo**: 1-2 agents em paralelo, sequencial o resto. Sem mass-spawn. Sem rotação de chaves.
**Skill orquestradora**: `~/.mavis/skills/prompt-cartorio/SKILL.md` ← briefing canônico recarregável.

## Briefing Gustavo 12:03 BRT (turno 2)
- NUNCA rotacionar chaves (reforço 4x) — regra absoluta
- OpenClaw deepseek-v4-flash: ativar thinking + restaurar contexto 1M (atual 131.1k, bug config)
- Telegram bot test_cartorio conectar e validar E2E
- 100 tasks (este roadmap + ROADMAP_100MELHORIAS.md = cobertura full)
- API + N8N centrais; Supabase central usar TUDO (Vault + Cron + Webhooks + Queues + GraphQL)
- Chatwoot = CRM + pause/resume agent; OpenClaw = cérebro agent AI sério/direto/sem emoji
- OpenCode Zen + Qwen Coder pra tarefas simples
- Codex-bar pra monitorar tokens
- Não refazer, só melhorar; 1-2 agents max paralelo; report binário
- Última coisa é só conectar WhatsApp — todo o resto tem que estar 100% pronto

---

## Estado atual (snapshot 11:43 BRT)

### Stack em prod (10/13 UP)
| Serviço | Status | Detalhe |
|---|---|---|
| API FastAPI v0.5.0 | ✅ | 19 endpoints, audit chain position 249, MCP 5/164 |
| Evolution 2.3.7 | ✅ | 1 instance `cartorio-2notas` em `connecting` (aguarda QR scan) |
| N8N | ✅ | healthz OK, 17 WFs, 12 ativos |
| OpenClaw Gateway | ✅ HTTP plain :18789 | `/v1/chat` 404 (BUG) |
| Supabase (13 svcs) | ✅ | Todos UP 19-20h healthy, SCRAM P0 resolvido |
| Redis 8.8 | ✅ PONG | UP 21h |
| Easypanel | ✅ | admin OK |
| Chatwoot (DNS) | ❌ NXDOMAIN | DNS pendente (SUI) |
| LiteLLM | ❌ NÃO EXISTE | env da API aponta mas container não roda |
| Radar | ❌ TCP-only RED | falso positivo, fix no Sprint 4 |

### Pendências SUI (só Gustavo resolve)
- 1.1 DNS `chatwoot.2notasudi.com.br` (Easypanel UI)
- 1.2 Credencial Evolution API no N8N (N8N UI)
- 1.3 Agent Bot Chatwoot "Cartório Assistant"
- 1.4 Regenerar Easypanel API key (exposta) → **DECIDIDO: NÃO rotacionar**
- 1.5 OpenClaw LLM key (depende L1 LGPD)
- 1.6 Decisão DNS typo `supbase` → `supabase` (cosmético)
- **BÔNUS**: QR scan do WhatsApp Business (instance `cartorio-2notas` pronta)

### Pendências código (Sprint 3, sequência após Sprint 2 ✅)
- E1.S2.T10 LGPD-016 #13 output scrub FULL COVERAGE (cartorio-dev, em andamento)
- LGPD-016 P1.7 timeline DPO + runbook (cartorio-lgpd)
- M4.x N8N workflows consolidação (cartorio-n8n, M2.7 done, faltam M4.1-M4.5)
- B1 Chatwoot restart loop (ADR-015)
- B2 OpenClaw context overflow (ADR-016)

---

## SPRINT 4 — Estabilizar + Fechar WhatsApp (24-30/06, ~25 tasks)

**Meta**: 1 cliente real conectado via WhatsApp. Chatwoot respondendo. Bot pausável.

### Fechar WhatsApp (3 tasks — SUI + auto)
- [ ] **T4.1** Gustavo: QR scan instance `cartorio-2notas` (5min)
- [ ] **T4.2** cartorio-n8n: configurar webhook global EVO → N8N (callback flow `webhook_evolution`)
- [ ] **T4.3** cartorio-n8n: configurar webhook EVO → API direta (`/api/v1/webhook/evolution`)

### Chatwoot (5 tasks)
- [ ] **T4.4** Gustavo: criar DNS A `chatwoot.2notasudi.com.br` (Easypanel UI)
- [ ] **T4.5** Gustavo: gerar CHATWOOT_API_KEY + CHATWOOT_BOT_TOKEN (Chatwoot UI)
- [ ] **T4.6** cartorio-dev: injetar CHATWOOT_API_KEY no env da API (Swarm service update)
- [ ] **T4.7** cartorio-n8n: WF #03 handoff humano já existe, validar integração EVO↔Chatwoot
- [ ] **T4.8** cartorio-lgpd: revisar CHATWOOT_API_KEY lifecycle (não expor em logs)

### OpenClaw Agent infra (4 tasks)
- [ ] **T4.9** cartorio-dev: corrigir `/v1/chat` 404 (adicionar rota REST + WebSocket fallback)
- [ ] **T4.10** cartorio-dev: configurar LLM key no env (decidir: LiteLLM ou OpenClaw direto)
- [ ] **T4.11** cartorio-lgpd: DPA MiniMax assinado (LGPD-011 P0)
- [ ] **T4.12** cartorio-dev: LGPD-016 #13 output scrub FULL COVERAGE (E1.S2.T10, em andamento)

### Radar + observabilidade (4 tasks)
- [ ] **T4.13** cartorio-dev: fix `/api/v1/health/radar` (multi-probe real, não TCP-only)
- [ ] **T4.14** cartorio-dev: integrar `services/metrics.py` em `/api/v1/metrics/prometheus` (já feito P1.1)
- [ ] **T4.15** cartorio-dev: configurar Grafana Cloud ou self-hosted (decidir)
- [ ] **T4.16** cartorio-dev: alertas PagerDuty/Telegram para RED (cron já faz, falta notif)

### Supabase central setup (5 tasks)
- [ ] **T4.17** cartorio-dev: ativar Supabase Vault (encryption at rest)
- [ ] **T4.18** cartorio-dev: ativar Supabase Cron (Edge Functions scheduled)
- [ ] **T4.19** cartorio-dev: ativar Supabase Webhooks (database webhooks)
- [ ] **T4.20** cartorio-dev: ativar Supabase Queues (background jobs)
- [ ] **T4.21** cartorio-dev: configurar Supabase GraphQL (introspection + RLS)

### Estabilização infra (4 tasks)
- [ ] **T4.22** cartorio-dev: B1 Chatwoot restart loop fix (ADR-015: `docker service update --limit-memory 1G`)
- [ ] **T4.23** cartorio-dev: B2 OpenClaw context overflow (ADR-016: threshold 50 msgs + TTL 24h)
- [ ] **T4.24** cartorio-dev: watchdog persistente `cartorio-evo-network-fix` (cron 5min, systemd morre)
- [ ] **T4.25** cartorio-lgpd: revisar `cartorio-evo-network-fix.sh` (PII em env vars, scruba)

---

## SPRINT 5 — Documentação completa das plataformas (1-7/07, ~25 tasks)

**Meta**: time novo onboarda em 1 dia lendo `docs/`. Cada plataforma tem doc canônica em `docs/platforms/`.

### Documentação plataformas (5 tasks)
- [ ] **T5.1** cartorio-dev: `docs/platforms/evolution-api.md` (autenticação, instances, webhooks, eventos, troubleshooting)
- [ ] **T5.2** cartorio-n8n: `docs/platforms/n8n.md` (workflows, credentials, expressions, executions, debug)
- [ ] **T5.3** cartorio-lgpd: `docs/platforms/chatwoot.md` (agents, inboxes, conversations, bots, audit)
- [ ] **T5.4** cartorio-dev: `docs/platforms/supabase.md` (DB, Auth, Storage, Realtime, Edge Functions, Vault, Cron, Queues, GraphQL)
- [ ] **T5.5** cartorio-dev: `docs/platforms/redis.md` (cache, rate limit, pub/sub, streams, persistence)

### Documentação interna (5 tasks)
- [ ] **T5.6** cartorio-dev: `docs/API.md` completa (19 endpoints + payloads + erros + exemplos curl)
- [ ] **T5.7** cartorio-dev: `docs/ARCHITECTURE.md` atualizar (audit chain, PII 3 camadas, HITL, emolumento MG)
- [ ] **T5.8** cartorio-lgpd: `docs/LGPD_COMPLIANCE.md` (RIPD, retenção, consentimento, DPO, direito titular)
- [ ] **T5.9** cartorio-dev: `docs/RUNBOOK.md` (operação diária, incidentes comuns, rollback)
- [ ] **T5.10** cartorio-n8n: `docs/N8N_WORKFLOWS.md` atualizar (17 WFs + diagrama fluxo)

### ADRs (5 tasks — Architecture Decision Records)
- [ ] **T5.11** cartorio-dev: ADR-019 Supabase central (vault + cron + queues)
- [ ] **T5.12** cartorio-dev: ADR-020 OpenClaw direct vs LiteLLM (decisão LiteLLM)
- [ ] **T5.13** cartorio-dev: ADR-021 N8N 2.x auth pattern (cookie + API key)
- [ ] **T5.14** cartorio-dev: ADR-022 IP /24 truncation LGPD-by-design (D5)
- [ ] **T5.15** cartorio-lgpd: ADR-023 DPA MiniMax (LGPD art. 33)

### Memory + lessons (5 tasks)
- [ ] **T5.16** Pietra: consolidar MEMORY.md (Lessons 30-37 em arquivo único)
- [ ] **T5.17** cartorio-dev: lessons 30+ específicas do cartório (CRUD, audit, PII, FastAPI)
- [ ] **T5.18** cartorio-n8n: lessons 20+ específicas N8N (workflow design, expressions, retry)
- [ ] **T5.19** cartorio-lgpd: lessons 15+ LGPD (consentimento, retenção, PII anchored regex)
- [ ] **T5.20** Pietra: cross-project lessons unificadas em `~/.mavis/agents/mavis/memory/MEMORY.md`

### Changelogs (5 tasks)
- [ ] **T5.21** cartorio-dev: CHANGELOG.md v0.5.0 → v0.7.0 (Sprint 3 + 4 features)
- [ ] **T5.22** cartorio-n8n: changelog workflows (12 ativos, 5 inativas, 3 novos Sprint 4)
- [ ] **T5.23** cartorio-lgpd: changelog compliance (LGPD-011 a LGPD-016)
- [ ] **T5.24** Pietra: changelog infra (VPS, Swarm, Traefik, DNS, certs)
- [ ] **T5.25** Pietra: postmortem 23/06 P0 Supabase SCRAM (aprender com incidente)

---

## SPRINT 6 — Cobertura + Compliance (8-14/07, ~25 tasks)

**Meta**: 95% coverage + LGPD-016 fechado + audit externo

### LGPD-016 fechamento (6 tasks)
- [ ] **T6.1** cartorio-lgpd: P1.7 timeline DPO + runbook (24h resposta ANPD)
- [ ] **T6.2** cartorio-lgpd: P1.5 PIS/PASEP anchored regex (já tem no pii.py, validar suite teste)
- [ ] **T6.3** cartorio-lgpd: P1.6 RIPD auditoria anual (template + checklist)
- [ ] **T6.4** cartorio-lgpd: P2.1 consentimento granular por canal (WhatsApp vs Telegram vs Web)
- [ ] **T6.5** cartorio-lgpd: P2.2 retenção 5y/até-revogação configurável
- [ ] **T6.6** cartorio-lgpd: P2.3 backup criptografado at-rest (S3 SSE-KMS)

### Testes + cobertura (5 tasks)
- [ ] **T6.7** cartorio-dev: aumentar coverage 91% → 95% (audit + pii + emolumento)
- [ ] **T6.8** cartorio-dev: testes E2E Playwright (chat WhatsApp simulado)
- [ ] **T6.9** cartorio-dev: testes de carga (Locust, 100 req/s sustentado)
- [ ] **T6.10** cartorio-dev: testes de caos (desligar Redis, ver fallback)
- [ ] **T6.11** cartorio-dev: property-based testing em PII scrubber (hypothesis)

### Auditoria externa (4 tasks)
- [ ] **T6.12** Gustavo: contratar auditoria LGPD third-party (R$ 5-15k)
- [ ] **T6.13** cartorio-lgpd: pentest API (OWASP top 10)
- [ ] **T6.14** cartorio-lgpd: scan segredos em código (gitleaks + trufflehog)
- [ ] **T6.15** cartorio-lgpd: revisão DPA fornecedores (MiniMax, Hostinger, Easypanel, Cloudflare)

### Hardening segurança (5 tasks)
- [ ] **T6.16** cartorio-dev: rate limit por sessão (já tem Redis sliding window, expor em /metrics)
- [ ] **T6.17** cartorio-dev: WAF Traefik (CrowdSec + fail2ban integration)
- [ ] **T6.18** cartorio-dev: rotação de secrets (Vault UI Supabase, 90d)
- [ ] **T6.19** cartorio-dev: CSP + CORS restritivo (admin + app)
- [ ] **T6.20** cartorio-dev: 2FA admin (TOTP, obrigatório)

### Operação (5 tasks)
- [ ] **T6.21** cartorio-dev: backup S3 automatizado (restic + boto3)
- [ ] **T6.22** cartorio-dev: restore test mensal (validar backup é restaurável)
- [ ] **T6.23** cartorio-dev: log aggregation (Loki + Grafana ou Sentry)
- [ ] **T6.24** cartorio-dev: incident response plan (Grave 1/2/3)
- [ ] **T6.25** cartorio-dev: post-mortem template (blameless)

---

## SPRINT 7 — Operação + Escala (15-21/07, ~25 tasks)

**Meta**: 5 cartórios em produção simultâneo. Operação 24/7.

### Multi-cartório (5 tasks)
- [ ] **T7.1** cartorio-dev: schema multi-tenant (cartorio_id em todas tabelas)
- [ ] **T7.2** cartorio-dev: subdomain routing (1cart.2notasudi.com.br, 2cart..., wildcard cert)
- [ ] **T7.3** cartorio-dev: admin central (lista cartórios, métricas, billing)
- [ ] **T7.4** cartorio-n8n: WF templates parametrizados por cartório
- [ ] **T7.5** cartorio-lgpd: DPA por cartório (cada um assina o seu)

### Operação 24/7 (5 tasks)
- [ ] **T7.6** cartorio-dev: PagerDuty integration (quem é on-call)
- [ ] **T7.7** cartorio-dev: status page (status.2notasudi.com.br)
- [ ] **T7.8** cartorio-dev: error budget (SLO 99.5% = 3.6h downtime/mês)
- [ ] **T7.9** cartorio-dev: capacity planning (prever quando dobrar VPS)
- [ ] **T7.10** cartorio-dev: disaster recovery (região secundária, replicação async)

### AI infra scale (5 tasks)
- [ ] **T7.11** cartorio-dev: LiteLLM criar com Claude Opus 4.5 + Sonnet 4.5 (decidir)
- [ ] **T7.12** cartorio-dev: cost guardrail LLM (max $X/dia, circuit breaker)
- [ ] **T7.13** cartorio-dev: model fallback (se Opus cai, vai pra Sonnet)
- [ ] **T7.14** cartorio-dev: response cache semântico (Redis + embedding)
- [ ] **T7.15** cartorio-dev: prompt versioning + A/B test (LangSmith ou próprio)

### Multi-canal (5 tasks)
- [ ] **T7.16** cartorio-n8n: Telegram bot oficial (já tem teste, falta prod)
- [ ] **T7.17** cartorio-n8n: Webchat widget (admin embed)
- [ ] **T7.18** cartorio-n8n: Email integration (IMAP/SMTP pra protocolo)
- [ ] **T7.19** cartorio-n8n: SMS fallback (Twilio, opt-in)
- [ ] **T7.20** cartorio-n8n: Voice (URA, transcrição)

### Prospecção (5 tasks)
- [ ] **T7.21** Pietra: lista 50 cartórios SP (prospecção outbound)
- [ ] **T7.22** cartorio-n8n: template email apresentação (R$ X/mês)
- [ ] **T7.23** cartorio-n8n: landing page (cartorio-2notas.com.br landing)
- [ ] **T7.24** Pietra: demo agendada 5 cartórios (calendly + Zoom)
- [ ] **T7.25** Pietra: 2 cartórios fechados MVP pago (meta Sprint 7 final)

---

## Regra de ouro

**Tudo que está acima é roadmap. Nada é承诺 de execução imediata.**

Gustavo escolhe o que entra no sprint ativo. Squad executa 5-7 tasks por sprint por agent, sequencial, com qualidade.

Toda task que toca `audit`, `pii`, `consentimento`, `retenção` ou LGPD exige:
1. Implementação (cartorio-dev ou cartorio-n8n)
2. Cross-review (cartorio-lgpd)
3. ASSINURA antes de merge (status `LGPD-APPROVED`)

Cross-review pendente agora:
- ✅ E1.S2.T9 IP /24 truncation (commit `5ca849c`, assinado na próxima sprint)
- ⏳ E1.S2.T10 LGPD-016 #13 output scrub FULL COVERAGE (em andamento)

---

## Tokens & eficiência

- 1 agent paralelo = ~2k tokens/tick
- 2 agents paralelos = ~4k tokens/tick
- Squad ideal: 1 cartorio-dev em task longa + 1 cartorio-lgpd em review = 4k/tick
- Pietra orquestrador = ~1k tokens/tick (este doc + monitor + crons)

Limite Gustavo: 5h reset, ~1d 19h semanal. Usar 1-2 agents paralelos = ~30-60min sustentado sem estourar.

**Sem mass-spawn. Sem rotação. Sem ativar 50 skills de uma vez. Cada task puxa o que precisa.**

Modified by Gustavo Almeida
