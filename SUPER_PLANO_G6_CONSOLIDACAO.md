# CICLO G6 — Consolidação Pós-Super Plano v25
**Cartório 2º Notas Uberlândia — Projeto Agent AI Multicanal**
**Versão:** G6.0 — 2026-07-16
**Modified by:** Gustavo Almeida + Pietra orquestrador
**Status:** 🟢 WAVES 1–13 DONE · herda em **G7** (`SUPER_PLANO_G7_100_TASKS.md`)

---

## 🎯 META ÚNICA

> **Levar o projeto do estado pós-F6 (2861 pytest / mypy 0 / ruff 0 / coverage 95%) para G6-milestone: 3000+ tests, coverage ≥96%, mutation testing baseline, end-to-end robustness nos 6 serviços prod UP, e fechar 20 tasks REALISTAS no TASKS.md (filtradas para o que dá pra fazer AGORA sem SSH/UI Gustavo).**

### Critérios de completion
1. ✅ 3000+ pytest passing
2. ✅ Coverage ≥96% (subida de 95% → 96%)
3. ✅ Mutation testing baseline (mutmut ≥75% killed em audit+pii)
4. ✅ 6 serviços prod UP (api/agent/easypanel + 3 a recuperar via Gustavo SUI)
5. ✅ 20 tasks fechadas em `.harness/TASKS.md` com Conventional Commits
6. ✅ 1 push master sem conflito

---

## 🏗️ SQUADS G6 (4 squads × 5 tasks = 20 tasks, modo 1-2 agents/loop)

### G6.A — BACKEND HARDENING (cartorio-dev)
1. **G6.A.T1** mutation testing baseline (mutmut em `audit.py` + `pii.py`, target ≥75% killed)
2. **G6.A.T2** property-based tests LGPD consent/retention (Hypothesis, 1000 iterações)
3. **G6.A.T3** OpenAPI snapshot test (gera spec.json, compara em CI)
4. **G6.A.T4** pytest-xdist paralelo (ganho de tempo suite ~30%)
5. **G6.A.T5** coverage fail-safe se cair <96% (script Makefile + CI gate reforçado)

### G6.B — N8N + INTEGRAÇÕES (cartorio-n8n)
1. **G6.B.T1** workflow validator CI (`scripts/n8n_workflow_validator.py` gate merge)
2. **G6.B.T2** canned responses jurídicas 10/50 (templates atos: certidão, procuração, escritura)
3. **G6.B.T3** Evolution dual-format parse coberto por teste de fuzz (hypothesis)
4. **G6.B.T4** WF `lgpd-audit-diario` skeleton (cron 03:00 BRT, ANPD-ready counts)
5. **G6.B.T5** `infra/n8n-workflows/INDEX.md` auto-gerado (registry dos 34 WFs)

### G6.C — LGPD / COMPLIANCE (cartorio-lgpd)
1. **G6.C.T1** RIPD v1.4 addendum (incluir integração LobeChat + OpenClaw)
2. **G6.C.T2** DPA MiniMax template revisado (campos: data residency, retention, sub-processor)
3. **G6.C.T3** propriedade de retenção: tests Hypothesis validam 5y/2y/90d
4. **G6.C.T4** `D5 IP truncation` regression test (provar que PII truncado em todos payloads)
5. **G6.C.T5** Privacy Policy v3 (atualizar com LiteLLM + MiniMax provider + sub-processors)

### G6.D — SRE / OBSERVABILITY (cartorio-sre)
1. **G6.D.T1** Health check expandido `/api/v1/health/radar` (10 domínios, output JSON)
2. **G6.D.T2** Prometheus alert rules (5min DOWN → Telegram GRUPO PIETRA)
3. **G6.D.T3** Backup dry-run script (`scripts/backup_dryrun.sh` valida restore sem subir prod)
4. **G6.D.T4** Grafana dashboard spec (JSON, 9 painéis)
5. **G6.D.T5** Runbook final DNS Cloudflare (merge com infra/dns/CLOUDFLARE_RUNBOOK.md)

---

## 🚦 VALIDAÇÃO FINAL

- [ ] 20 tasks com `[x]` em `.harness/TASKS.md`
- [ ] 5+ commits Conventional Commits (1 por squad mínimo)
- [ ] pytest 3000+ passed
- [ ] coverage ≥96%
- [ ] mypy 0 / ruff 0 / mutation ≥75% killed
- [ ] push master sem conflito

---

## ⚠️ SUI (Só Gustavo Resolve) — pendentes para próxima sessão

1. DNS Cloudflare 3 A records (chatwoot/n8n/supabase)
2. 3 env vars Easypanel UI (evolution/chatwoot/n8n DATABASE_URL)
3. Telegram token BotFather regenerar
4. LobeChat OPENAI_API_KEY real (substituir sk-xxxx)
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E8 cartorio-bot (SSH VPS bloqueado)

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 09:45 BRT**
