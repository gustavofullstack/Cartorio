# GOALS — Cartório 2º Notas · 2026-07-03

> Single source of truth de metas do projeto. Formato: **letra → objetivo → status → % → evidência**.
> Sincronizado com `.harness/paperclip-board/board.json` (G1-G5) e `.harness/loop-engineer/crons/LOOP_OBJECTIVE.md`.
> Atualizado por loop-engineer cron + agent harnesso. Append-only via PROGRESS.md.

---

## META ÚNICA

**Cartório 2º Notas 100% production-ready com WhatsApp produção conectado** via Evolution API + LGPD 100% + fallback chain validado 3x.

---

## GOALS A-G (consolidado 2026-07-03)

| Letra | Objetivo | Status | % | Evidência |
|-------|----------|--------|---|-----------|
| **A** | API + audit chain + PII production-grade | ✅ done | 100% | 1648 pytest passed, mypy 0, ruff 0 (PROGRESS 2026-07-02) |
| **B** | Telegram bot live + Chatwoot inbox 1 | ✅ done | 100% | lesson 137 — 9 E2E tests, latency 10-15s |
| **C** | LGPD compliance 100% | ✅ done | 95% | squad D 100% + DPA DeepSeek (lesson 138) |
| **D** | WhatsApp Evolution API conectado | 🟡 blocked | 30% | SUI Gustavo (QR scan whatsapp.2notasudi.com.br/manager) |
| **E** | Loop engineer auto-reactivação | ✅ done | 95% | 5 agents + cron scripts + state machine + loop-continue (Lesson 139-140) |
| **F** | Docs sincronizadas turn 50+ | 🟡 in_progress | 20% | synced via loop |
| **G** | Multi-provider fallback validado | 🟡 in_progress | 20% | loop integration progressing |

## SQUAD STATUS (validado cycle 140)

| Task | Status | Evidência |
|------|--------|-----------|
| J7 ci.yml | ✅ done | `.github/workflows/ci.yml` 212 linhas (lint+mypy+pytest+coverage+codecov) |
| J8 cd.yml | ✅ done | `.github/workflows/cd.yml` 107 linhas (Render API + polling + GH comment) |
| J9 Sentry SDK | ✅ done | `app/services/sentry.py` 153 linhas + PII scrubber + 29 tests passing |
| J10 OTel collector | ✅ done | `infra/observability/otel-collector-config.yml` + 6 tests J10 + 11 tracing tests |
| J6 Render health custom | ⏸️ blocked | script+curl ready em `docs/j6-j10-ci-cd-2026-06-25.md` — falta SUI Gustavo (RENDER_API_KEY + service config) |

---

## MAPPING PAPERCLIP → GOALS

| Paperclip G | → | Goal |
|-------------|---|------|
| G1 — 7/7 services 72h stable | → | A + D |
| G2 — Bot Telegram prod-ready | → | B |
| G3 — LGPD 100% | → | C |
| G4 — Docs turn 50 sync | → | F |
| G5 — Loop engineer auto-reactivação | → | E |

---

## NEXT CYCLE TARGETS (do LOOP_OBJECTIVE.md + PLAN_100_TASKS_LOOP.md)

### P0 (próximos 5 cycles)
- [ ] D — Fechar WhatsApp QR scan (SUI Gustavo)
- [ ] E — Instalar launchd plist (goal-loop 4h + intensive 30min)
- [ ] F — Sync PROMPT.json/MD turn 50 (T9)
- [ ] G — Testar fallback opencode_go → opencode_free_1 → opencode_free_2 (3x)

### P1 (cycles 6-10)
- [ ] Squad C docs 100% (12/25 → 25/25)
- [ ] Squad J obs+CI/CD (5/10 → 10/10)
- [ ] pytest 1648 → 1300+ (meta antiga, hoje já superado)
- [ ] coverage 30.7% → 90% (DEP-1)

### P2 (cycles 11+)
- [ ] Brain endpoints BRAIN3/4/8
- [ ] Squad E last task (E08)
- [ ] Audit log em 100% mutações com request_id/ip/user_agent (Sprint 3 Goal 4.1)

---

## SUI — Só Gustavo Resolve (BLOCKERS HUMANOS)

1. **DNS Cloudflare**: `n8n.2notasudi.com.br` + `supabase.2notasudi.com.br` → A record 187.77.236.77
2. **WhatsApp QR**: `whatsapp.2notasudi.com.br/manager` → Instância `cartorio-2notas` (state=close)
3. **Testar Telegram Bot**: Mandar msg para @CartorioAssistantBot e confirmar recepção no Chatwoot
4. **DNS typo**: `supbase` → `supabase` (decisão pendente)
5. **Easypanel API key** rotacionada (exposta)
6. **OpenClaw LLM key** (depende L1 LGPD)

---

## HOW THIS FILE IS UPDATED

- **Manual**: Gustavo edita direto após milestone
- **Loop cron**: `goal-loop-cron.sh` append em PROGRESS.md (não toca GOALS.md)
- **Harness**: `.harness/agent.md` referencia este arquivo como source of truth
- **Agents**: 01-analyze-agent.sh lê este arquivo no `analyze` phase

---

Modified by Gustavo Almeida (via plan Mavis)