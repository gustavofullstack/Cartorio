# G7 Progress Dashboard — Integração Total

**Atualizado:** 2026-07-17 Wave **26 DONE** · **75/100 tasks** · waves 24–26 agent-side  
**Comando live:** `python3 scripts/g7_orchestrator.py status` · `make g7-validate` · `make g7-composite`  
**Progress append:** `make g7-progress WAVE=N SUMMARY="..."` · `python3 scripts/g7_progress_append.py --wave N --summary "..."`  
**TG 1000 subset:** `python3 scripts/telegram_1000_subset_check.py`

---

## Scorecard

| Dimensão | % | Notas |
|----------|---|--------|
| Super plano 100 tasks | **~62–68%** | W13–25 + W26 A4 (KISS N8N + pre-commit + TG1000) |
| Backend qualidade | **~93–96%** | mypy 0; 5 gap mods @100%; 18 tests W24 |
| Prod integração MVP | **~55–60%** | cut-line doc OK; WA QR + 502 ainda SUI HOLD |
| Validador local | WORK | composite import exit 0; TG1000 subset 31/31 |
| Validador prod | HOLD | dns NXDOMAIN + radar red |
| Composite gate (W24) | WORK | `make g7-composite` exit 0/1/2 |
| CD / MVP docs (W25 A4) | WORK | EasyPanel hook + MVP cut-line + LE monitor |
| N8N KISS / pre-commit / TG1000 (W26 A4) | WORK | inventory+1 archive; install doc; subset auto |

---

## Waves Grok (resumo)

| Wave | Entrega chave |
|------|----------------|
| 13–16 | RIPD, mutation killers, CI, HMAC PREV, board |
| 17–18 | Dual-format WA, WS50, Postman, rate-limit metrics, DLQ, TG plain |
| 19–20 | PII 8/8, OpenAPI 126, TG multi-turn, Evolution checklist, SUPER_STATUS |
| 21 | TG setWebhook helper, smoke 26, LobeChat secret scrub, mutmut status |
| 22 | Coverage gap report, canned v4, WA emolumento synth, DNS SUI pack |
| 23 | DMS/evo coverage tests, Chatwoot bot setup, LobeChat key runbook, dashboard |
| **24** | **DONE** alembic head 0020, backup dry-run, 502 playbook, mypy gate, composite gate, progress append, 18 coverage tests |
| **25** | **DONE (docs agent-side)** RLS sample, pool report, CD EasyPanel hook, MVP cut-line, cert LE monitor, skills smoke |
| **26** | **IN PROGRESS** N8N KISS inventory, pre-commit install doc, TG 1000 subset auto (+ parallel MCP/WS/Tailscale) |

---

## Wave 26 — IN PROGRESS (4 agents / slots)

| Slot | Rein | Tasks | Entrega | Status |
|------|------|-------|---------|--------|
| A1 | (parallel) | G7.09.* / MCP / coding-vps | smoke MCP + coding-vps | parallel |
| A2 | (parallel) | G7.10 / G7.11 / Tailscale | WS + Tailscale follow-ups | parallel |
| A3 | (parallel) | G7.14 / G7.19 / G7.20.T2 | skills registry / data inv / service extract | parallel |
| **A4** | **cartorio-n8n/brain** | **G7.20.T4 + G7.22.T3 + G7.24.T2** | **`docs/N8N_EXPORTS_KISS_G7.md` + `docs/PRECOMMIT_INSTALL_G7.md` + `scripts/telegram_1000_subset_check.py`** | **DONE (docs/script, no prod, no commit)** |

### A4 notes (2026-07-17)

- **G7.20.T4 KISS N8N:** auditoria de `infra/n8n-workflows/` — 0 hash dups; 1 near-dup arquivado (`lgpd-esqueci-fix.json` → `backups/kiss-g7-2026-07-17/`); 38 JSONs raiz; prefix clashes inventariados (sem rename mass).
- **G7.22.T3 pre-commit:** guia all-devs a partir de `.pre-commit-config.yaml` (7 hooks local/system) + skip/troubleshoot + vs `make pre-commit`/`make qa`.
- **G7.24.T2 TG1000 subset:** script offline 31 checks (docs, 7 cmds, endpoints, pytest, scripts) — **31/31 WORK**; report `docs/TELEGRAM_1000_SUBSET_REPORT_G7.md`.
- **Sem commit / sem mutação prod** neste slot.

### Tasks W26 tracking (A4)

| ID | Título | Doc / Artefato | Agent |
|----|--------|----------------|-------|
| G7.20.T4 | KISS unused N8N exports | `docs/N8N_EXPORTS_KISS_G7.md` + archive kiss-g7 | A4 |
| G7.22.T3 | pre-commit install all devs | `docs/PRECOMMIT_INSTALL_G7.md` | A4 |
| G7.24.T2 | 1000-point Telegram subset auto | `scripts/telegram_1000_subset_check.py` + report | A4 |

---

## Wave 25 — DONE docs (preservada)

| Slot | Rein | Tasks | Entrega | Status |
|------|------|-------|---------|--------|
| A1 | cartorio-dev/sre | G7.08.T3 + G7.08.T4 | `docs/RLS_AUDIT_SAMPLE_G7.md` + `docs/CONNECTION_POOL_REPORT_G7.md` | agent-side DONE |
| A2 | (parallel) | G7.15.T* / G7.20.* | `docs/SKILLS_SMOKE_G7.md` (se aplicável) + SOLID follow-ups | check parallel |
| A3 | (parallel) | TBD wave board | — | — |
| **A4** | **cartorio-sre/brain** | **G7.22.T2 + G7.23.T4 + G7.13.T1** | **`docs/CD_EASYPANEL_HOOK_G7.md` + `docs/MVP_CUTLINE_G7.md` + `docs/CERT_LE_EXPIRY_MONITOR_G7.md`** | **DONE (docs, no prod mutate)** |

### A4 notes W25 (2026-07-17)

- **CD:** prod canônico = EasyPanel+Swarm; `cd.yml`=Render legado; `deploy.sh` EasyPanel API ainda TODO; health/radar/rollback documentados.
- **MVP cut-line:** WhatsApp **emolumento consult only** + protocolo read-only + HITL DRAFT; emissão/pagamento/SaaS OUT; go-live subset M1–M8.
- **LE monitor:** openssl `-checkend` 21d/7d nos 7 FQDNs canônicos; cron/script follow-up opcional.

### Tasks W25 tracking

| ID | Título | Doc | Agent |
|----|--------|-----|-------|
| G7.08.T3 | RLS audit sample | `docs/RLS_AUDIT_SAMPLE_G7.md` | A1 |
| G7.08.T4 | Connection pool report | `docs/CONNECTION_POOL_REPORT_G7.md` | A1 |
| G7.13.T1 | Cert LE expiry monitor | `docs/CERT_LE_EXPIRY_MONITOR_G7.md` | A4 |
| G7.22.T2 | CD EasyPanel hook documentado | `docs/CD_EASYPANEL_HOOK_G7.md` | A4 |
| G7.23.T4 | MVP cut-line WA consult only | `docs/MVP_CUTLINE_G7.md` | A4 |
| G7.15.T2–T4 | skills smoke/map | `docs/SKILLS_SMOKE_G7.md` (parcial) | parallel |
| G7.20.T1/T3 | SOLID/Any hotspots | `docs/SOLID_DEAD_CODE_AUDIT_G7.md` + `ANY_HOTSPOTS_G7.md` | W25 |

---

## Wave 24 — 4 agents / 4 slots (DONE — não apagar)

| Slot | Rein | Tasks | Entrega |
|------|------|-------|---------|
| A1 | cartorio-dev | G7.08.T1 + G7.21.T1 | `docs/ALEMBIC_HEADS_REPORT_G7.md` + `MYPY_STRICT_GATE_G7.md` + `scripts/check_alembic_single_head.py` |
| A2 | cartorio-sre | G7.08.T2 + G7.13.T3 | `docs/BACKUP_DRYRUN_REPORT_G7_WAVE24.md` + `PLAYBOOK_502_VS_NXDOMAIN_G7.md` |
| A3 | cartorio-dev | G7.01.T2+ | `backend/tests/test_g7_wave24_integration.py` (18 passed; 5 mods 100%) |
| A4 | cartorio-brain/sre | G7.24.T3 + G7.23.T3 | `g7_composite_gate.py` + `g7_progress_append.py` + Makefile targets |

### Exit codes (`make g7-composite`)

| Code | Meaning |
|------|---------|
| `0` | All local OK (prod WORK if checked) |
| `1` | Local fail (ruff / mypy / pytest / import) |
| `2` | Local OK, prod HOLD (dns / radar partial or unreachable) |

---

## SUI pack (bloqueia 100% prod)

1. `docs/DNS_TRAEFIK_SUI_PACK_G7.md`  
2. `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md`  
3. `docs/TELEGRAM_WEBHOOK_REREGISTER_G7.md`  
4. `docs/LOBECHAT_OPENAI_KEY_G7.md`  
5. `docs/CHATWOOT_AGENT_BOT_SETUP_G7.md`  
6. Redeploy API → `/radar/expanded` 200  
7. WhatsApp/Chat **502** upstream (Lesson 176 DATABASE_URL)  
8. MVP go-live subset → `docs/MVP_CUTLINE_G7.md` §6 (M1–M8)

---

## Próximos (W26 restante + follow-ups)

- Wire EasyPanel API em `scripts/deploy.sh` (remover TODO G7.22)
- Load test pool 25 (G7.08.T4 HOLD restante)
- Cron LE check em VPS (G7.13.T1 follow-up)
- G7.15 skills map final + G7.20.T2 service extract
- Confirmar N8N live IDs vs 38 exports; rename prefix clashes (opcional)
- SUI Gustavo: QR WA + DATABASE_URL evolution/chatwoot → prova G7-S2

---

## Artefatos canônicos

| Artefato | Path |
|----------|------|
| Plano 100 | `SUPER_PLANO_G7_100_TASKS.md` |
| Goals | `SUPER_GOALS_G7.md` |
| DoR/DoD | `docs/G7_DOR_DOD.md` |
| MVP cut-line | `docs/MVP_CUTLINE_G7.md` |
| CD EasyPanel | `docs/CD_EASYPANEL_HOOK_G7.md` |
| N8N KISS inventory | `docs/N8N_EXPORTS_KISS_G7.md` |
| Pre-commit install | `docs/PRECOMMIT_INSTALL_G7.md` |
| TG 1000 subset | `scripts/telegram_1000_subset_check.py` |
| TG 1000 report | `docs/TELEGRAM_1000_SUBSET_REPORT_G7.md` |
| Matrix | `docs/INTEGRATION_MATRIX_G7.md` |
| HTML status | `docs/SUPER_STATUS.html` |
| Composite | `scripts/g7_composite_gate.py` |

**Modified by Gustavo Almeida — G7 Wave 26 A4 (append; Waves 24–25 retained)**
