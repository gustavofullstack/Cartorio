# SUPER GOALS G7 — Integração Total Cartório
**Versão:** G7.0 — 2026-07-16  
**Meta única:** stack 100% integrado (API ↔ Telegram ↔ Chatwoot ↔ LobeChat ↔
Redis ↔ Postgres ↔ MCPs ↔ WS ↔ Webhooks ↔ Tailscale ↔ Proxy/DNS ↔ OpenClaw
agent ↔ tools/skills ↔ brain ↔ harness ↔ Postman/Swagger ↔ radar) com
qualidade SOLID/DRY/KISS, tipagem forte, CI/CD verde e MVP operacional.

---

## META (North Star)

> **Até 2026-07-31:** 9/9 canais health green, WhatsApp QR conectado, HITL
> escrevente em Chatwoot, OpenClaw cartorio-bot em produção, LGPD 100% com
> DPAs assinados, 3200+ pytest, coverage ≥96%, mutmut audit+pii ≥75%, zero
> P0 prod, loop harness contínuo.

---

## GOALS SUPER ROBUSTOS (G7.1 – G7.12)

| ID | Goal | % atual | Target | Evidence |
|----|------|---------|--------|----------|
| **G7.1** | API production-grade (audit+PII+emolumento+HITL) | 99% | 100% | mypy 0; W24 cov 5 mods 100%; 18 tests |
| **G7.2** | Telegram live E2E (webhook + memory + HITL) | 70% | 100% | token HOLD; 2268 LOC + tests |
| **G7.3** | Chatwoot handoff + inbox live | 42% | 100% | runbooks OK; DNS NXDOMAIN + 502 |
| **G7.4** | LobeChat agent cartorio | 62% | 100% | key runbook W23; env SUI |
| **G7.5** | Redis + Postgres + Supabase healthy 72h | 90% | 100% | alembic single head 0020; backup dry-run WORK |
| **G7.6** | MCP tools inventário + clients sync | 90% | 100% | 13 tools mcp_server; skills |
| **G7.7** | WebSockets + Webhooks dual-format | 95% | 100% | Evolution dual + WS tests |
| **G7.8** | Tailscale + Traefik + DNS Cloudflare | 60% | 100% | 502 playbook W24; 3 NXDOMAIN HOLD |
| **G7.9** | OpenClaw cartorio-bot + skills/brain | 50% | 100% | E6 spec + E2E scaffold |
| **G7.10** | Postman + Swagger + Radar + Agility board | 90% | 100% | composite gate + progress append |
| **G7.11** | SOLID/DRY/KISS + tipagem forte + OO | 94% | 100% | mypy 0 / 154 files gate doc |
| **G7.12** | CI/CD + observability + loop harness | 94% | 100% | g7-composite exit 0/1/2 |

**Média ponderada atual:** ~92–96% · **Meta G7:** ≥95% média, 0 P0.  
**Snapshot Wave 26 (2026-07-17):** super plano **75% done** (75/100 [x], 7 partial, 18 open — maioria SUI/prod).  
**Snapshot Wave 28 (2026-07-17):** super plano **~92% [x] / ~96% weighted** (~92/100 [x], ~8 [~], 0 [ ] open rows — residual live SUI: DNS A×3, env, tokens, QR, DPA sign, Privacy publish, AM secrets, Tailscale, OpenClaw scopes). Go-live pack: `docs/SUI_CHECKLIST_G7_WAVE28.md` · `docs/STABILITY_WINDOW_72H_G7.md` · lesson-206 · lesson-207.

**Snapshot Wave 28+ Resync (2026-07-17 ~17:30 BRT, Lesson 208):**
- 3 commits ahead origin pushed (b7ae85f → 6720d10): da176f9, 67d7a53, 6720d10
- Gates locais re-validados: pytest **3176**, mypy **155/155**, ruff **0**
- Working tree: 0 modified + 148 untracked (artefatos G7 W13-28 não-comitados)
- Orquestrador `scripts/super_loop_orchestrator.py` reporta `20/100` (lê `SUPER_PLANO_100_TASKS_25_SQUADS_v25.md` antigo). Gap conhecido: **script precisa apontar para `SUPER_PLANO_G7_100_TASKS.md`** (commit pending SUI #15)
- NÃO houve Wave 30 G6.A.T13/G6.D.T11 — tarefas equivalentes já entregues como G7 squads
- 15 SUI items ativos (lista atualizada em PROGRESS.md + lesson-208)

---

## SUPER OBJETIVO (scrum / MVP)

| Sprint | Foco | Done when |
|--------|------|-----------|
| **G7-S0** | Deploy gap close (redeploy API expanded + radar live) | `/radar/expanded` 200 |
| **G7-S1** | SUI Gustavo DNS+env+tokens (45min) | 7/7 radar services online |
| **G7-S2** | WhatsApp QR + Evolution dual + N8N WFs | 1 msg real WA→API→resposta |
| **G7-S3** | Telegram token + Chatwoot handoff | 1 msg TG→CW inbox |
| **G7-S4** | OpenClaw cartorio-bot + LobeChat key | agent responde 3 intents |
| **G7-S5** | LGPD DPA MiniMax + RIPD v1.4 sign-off | DPO assina |
| **G7-S6** | Coverage 96% + mutmut 75% audit/pii | gates CI |
| **G7-S7** | Postman/Swagger sync + docs agility | collection = OpenAPI |
| **G7-S8** | Loki/AlertManager/Prometheus live VPS | alert Telegram real |
| **G7-S9** | 72h stability + go-live checklist SUI | `.harness/SUI_CHECKLIST.md` |

---

## SUPER PROGRESSO (snapshot Wave 28 — 2026-07-17)

| Métrica | Valor |
|---------|-------|
| G7 waves agent-side | **13–27 DONE** · **28 go-live + SUI packs DONE agent-side** |
| G7 tasks closed (x) | **~92/100** |
| G7 partial (~) | **~8** (live SUI: WA real, DNS, handoff, TS, OpenClaw deploy, mutmut, SUI ticks…) |
| G7 open ( ) | **0** rows unmarked (all residual as [x] runbook or [~] live HOLD) |
| % progress | **~92% strict · ~96% weighted** |
| mypy / ruff | **0 / 0** (154 files W24 gate) |
| Alembic head | **0020 single** |
| Backup dry-run local | **WORK** (prod HOLD) |
| Composite gate local | **exit 0** / prod **exit 2 HOLD** |
| SUI blockers | ver `docs/SUI_CHECKLIST_G7_WAVE28.md` (DNS×3, env, tokens, QR, DPA, Privacy, AM, TS…) |
| 72h stability | **tracker ready** — window **NOT_STARTED** (`docs/STABILITY_WINDOW_72H_G7.md`) |
| Lessons | **207** (206 = consolidada G7 W13–28; 207 = Wave28 A4 SUI packs) |

### SUPER PROGRESSO (arquivo Wave 24 — 2026-07-17)

| Métrica | Valor |
|---------|-------|
| G7 waves agent-side | **13–24 DONE** |
| G7 tasks closed (x/~) | **~55/100** |
| pytest W24 new | **18 passed** (rate/sentry/radar) |
| mypy / ruff | **0 / 0** (154 files) |
| Alembic head | **0020 single** |
| Backup dry-run local | **WORK** (prod HOLD) |
| Composite gate local | **exit 0** / prod **exit 2 HOLD** |
| SUI blockers | DNS×3 + WA/CW 502 + tokens |
| Lessons | **196** |

---

## SUPER TESTE VALIDADOR (Definition of Done por wave)

Cada wave de 4 agents **só fecha** se:

1. `uv run ruff check app/` → 0
2. `uv run mypy app/` → 0
3. `uv run pytest -q --no-cov` → all pass (novos testes inclusos)
4. Conventional Commit + `Modified by Gustavo Almeida`
5. Lesson ou entry PROGRESS.md
6. Nenhum secret commitado (`scripts/secrets_scan.py` ou pre-commit)

---

## ORQUESTRAÇÃO (4 agents / squad)

| Slot | Rein | Papel |
|------|------|-------|
| A1 | `cartorio-dev` | API, tests, typing, audit/PII |
| A2 | `cartorio-n8n` | workflows, Evolution, webhooks |
| A3 | `cartorio-lgpd` | RIPD, DPA, IP, consent |
| A4 | `cartorio-sre` | DNS, radar, observabilidade, deploy docs |

**Regra projeto:** preferir **1-2 agents paralelos reais** (Lesson 185); simular
4 slots sequenciais no mesmo orchestrator quando CPU/SSH limitado.

**Loop:** analyze → test → fix → improve → optimize → document → comment → memory  
até 100 tasks G7 (`SUPER_PLANO_G7_100_TASKS.md`).

---

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16**  
**Wave 28 snapshot:** ~92–96% · lesson-206 consolidada · lesson-207 SUI packs · SUI_CHECKLIST_G7_WAVE28 · STABILITY_WINDOW_72H_G7 — 2026-07-17
