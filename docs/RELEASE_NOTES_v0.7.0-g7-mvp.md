# Release Notes — `v0.7.0-g7-mvp`

| Campo | Valor |
|-------|--------|
| **Tag (proposed)** | `v0.7.0-g7-mvp` |
| **Status** | 🟡 **NOTES READY · TAG HOLD** (needs Gustavo explicit approval — do **not** auto-tag) |
| **Task** | G7.25.T4 |
| **Wave** | G7 Wave 28 |
| **Scope** | SUPER PLANO G7 waves **13–28** (agent-side + SUI residual) |
| **Base** | pós-G6 consolidation · FastAPI cartório backend |
| **Date** | 2026-07-17 |

---

## 1. Summary (one paragraph)

**G7 Integração Total** takes the 2º Serviço Notarial de Uberlândia stack from post-G6 quality baseline (pytest ~3k, coverage ~95%, mutmut baseline 73%, mypy/ruff 0) to a **documented, agent-executable MVP cut-line**: WhatsApp **emolumento consult only** + protocolo **read-only** + mandatory HITL on any DRAFT protocolo, with audit chain, 3-layer PII, Redis idempotency, dual-format Evolution webhooks, Telegram/LobeChat/OpenClaw scaffolding, MCP tools, Traefik/DNS runbooks, LGPD RIPD v1.4 + DPA MiniMax **ready to sign**, and composite gates for CI. **Production go-live of all 9 channels remains SUI-gated** (DNS, QR, tokens, 72h stability). This tag marks **code+docs MVP readiness**, not “everything green in prod.”

---

## 2. What “G7 MVP” means

From `docs/MVP_CUTLINE_G7.md`:

> **MVP = consulta de emolumentos (e status de protocolo read-only) via WhatsApp, com LGPD/audit/PII e HITL obrigatório em qualquer rascunho de protocolo. Tudo que emite, cobra ou decide juridicamente sozinho está FORA.**

| IN MVP | OUT of MVP |
|--------|------------|
| WA Evolution dual-format webhook | Auto emissão certidão/escritura |
| Emolumento MG 2026 consulta | Pagamento / PIX / boleto |
| Protocolo status read-only | Decisão de isenção/urgência sozinha |
| Consent LGPD + PII 3 camadas | Multi-cartório SaaS |
| Audit append-only SHA256+HMAC | LobeChat público full agentic |
| Handoff humano (Chatwoot path) | Auto-book agenda binding |

---

## 3. Wave map 13–28 (highlights)

| Wave | Focus | Highlights |
|------|-------|------------|
| **W13** | Mutation + D5 + RIPD | Audit mutation killers; IP truncation D5; RIPD v1.4 addendum; canal health matrix |
| **W14** | Validator + MCP | `g7_super_validator.py`; MCP tool inventory; SUI Wave14 checklist |
| **W15** | OpenClaw + catalog | cartorio-bot JSON; WS/webhook Postman; skills index; Redis maxmemory doc |
| **W16** | CI + agility | HMAC webhook rotation checklist; CI openapi/n8n/coverage/secrets; DoR/DoD board |
| **W17** | Dual-format + WS | Evolution webhook Hypothesis dual-format; WS 50 concurrent mock; Postman regen; Tailscale offline runbook |
| **W18** | Metrics + TG | Rate-limit 3-tier Prometheus; DLQ admin drill; TG plain/Markdown (no HTML leak); MCP client example; DOMAIN_TYPO ratified |
| **W19** | PII + OpenAPI | PII pre-LLM inventory 8/8; OpenAPI 126 paths snapshot; Chatwoot handoff doc; redlock DMS peer |
| **W20** | TG hist + Evolution | Multi-turn Redis catalog; HMAC rotation drill; Evolution DATABASE_URL/QR checklist; SUPER_STATUS |
| **W21** | TG live prep + mutmut | setWebhook runbook/script; smoke inventory 26; LobeChat secret scrub; mutmut status report |
| **W22** | Coverage + WA synth | Coverage gap report; canned responses +10 jurídicas; WA→emolumento synthetic; DNS Traefik SUI pack |
| **W23** | Cov + bots | DMS/evo coverage tests; Chatwoot agent bot runbook; LobeChat OPENAI key runbook; progress dashboard |
| **W24** | Data + gates | Alembic single head **0020**; backup dry-run WORK; 502 vs NXDOMAIN playbook; mypy 0/154; composite gate exit 0/1/2; progress append |
| **W25** | RLS + MVP | RLS sample; pool report; skills 6/6 smoke; SOLID dead-code; Mapped 100%; CD EasyPanel hook; **MVP cut-line**; LE cert monitor |
| **W26** | MCP + OpenClaw | MCP mount smoke 13 tools; coding-vps 63 tools; WS ping/pong proxy; Tailscale restore/ACL docs; OpenClaw skills + 1M context; LGPD inventory 25 fields; N8N KISS archive; pre-commit install; TG1000 subset 31/31 |
| **W27** | Strict + edge + LGPD | Pydantic strict future flags; DRY mask_nome/email; Traefik access-log + edge RL docs; AlertManager→TG + Loki sample; DPA MiniMax READY; Privacy Policy v3 draft; 3 intents E2E synthetic; Traefik routers merge; radar redeploy runbook |
| **W28** | Mutmut + release | Killers audit+pii re-verify green; `MUTMUT_REPORT_G7_WAVE28.md`; **these release notes** (tag HOLD) |

---

## 4. Metrics snapshot (agent-side, Wave 28)

| Métrica | ~Valor | Notas |
|---------|--------|-------|
| SUPER_PLANO G7 tasks | **~88/100 [x]** (after W28 marks) | ~7 partial SUI, ~5 open |
| G7 waves agent-side | **13–28** | SUI residual parallel |
| pytest (order of magnitude) | **3200+** collect path / 3k+ suite | Exact count drifts with WIP |
| Coverage gate | ≥90% CI; goal ≥96% | Gap fills W22–W26 |
| mypy strict `app/` | **0 errors** (W24 gate, 154 files) | Hold zero regressions |
| ruff | **0** | `make lint` |
| mutmut aggregate | **73.0% killed** baseline | Target ≥75% — full re-run night HOLD |
| mutmut killers audit/pii | **177 passed** (W28) | `test_audit_mutation*`, pii, audit reg |
| Alembic | **single head 0020** | `check_alembic_single_head.py` |
| N8N webhooks idempotency | **22 validated** (doc) | calculator notice W26 |
| MCP tools (`mcp_server.py`) | **13** offline smoke | do not hardcode forever |
| TG 1000 subset | **31/31 WORK** | offline script |
| Composite gate local | **exit 0** | prod still HOLD (dns+radar) |
| MVP cut-line doc | **DONE** | `docs/MVP_CUTLINE_G7.md` |

*Numbers are engineering snapshots, not contractual SLAs. Prod radar may still be red until SUI.*

---

## 5. Security / LGPD highlights

- **HITL mandatory** — protocolo always `DRAFT` until escrevente.
- **PII 3 layers** — validators → Sentry `before_send` → log `MaskingFilter`.
- **Audit** — append-only SHA256 chain + HMAC; T024/T025 regression tests; rotation drill doc.
- **D5 IP truncation** — dual full/truncated IP in audit paths.
- **No literal key fallbacks** — `check_no_literal_keys.py` / secrets_scan CI.
- **RIPD v1.4** addendum (W13); **DPA MiniMax** READY_TO_SIGN (W27, sign SUI); Privacy Policy v3 draft (publish SUI).
- **LobeChat import scrub** (W21) — removed hardcoded apiKey from import JSON.

---

## 6. HOLD residual / SUI (blocks “prod MVP live”)

Do **not** treat tag as “all systems green.” Residual:

### 6.1 Hard SUI (Gustavo UI / secrets / DNS)

| Item | Task / doc | Why HOLD |
|------|------------|----------|
| DNS A records chatwoot/n8n/supabase | G7.12.T1, `DNS_TRAEFIK_SUI_PACK_G7.md` | NXDOMAIN aliases |
| dns-check Makefile exit 0 | G7.12.T2 | depends on live DNS |
| WhatsApp QR open + 1 msg real | G7.04.T4 | synthetic E2E only |
| Chatwoot DNS + Traefik | G7.05.T1 | NXDOMAIN / 502 |
| Chatwoot handoff prod | G7.05.T3 | checklist only |
| OpenClaw cartorio-bot deploy | G7.06.T3 | JSON ready, deploy SUI |
| LobeChat key / import UI | G7.06.T1/T2 | runbooks ready |
| Telegram BotFather token live | G7.03.T1 | runbook ready |
| Tailscale online + radar SSH | G7.11.T1/T2 | runbook + mapping HOLD |
| DPA MiniMax **sign** + Privacy **publish** | G7.19.T2/T3 | draft READY |
| AlertManager secrets live fire | G7.18.T3 | doc READY |
| Radar expanded prod redeploy | G7.18.T1 | runbook READY |
| SUI_CHECKLIST 100% tick | G7.25.T1 | open |
| 72h stability window | G7.25.T2 | open |
| Operator token scopes | G7.14.T4 | open |
| **git tag `v0.7.0-g7-mvp`** | G7.25.T4 | **this file only — tag HOLD** |

### 6.2 Agent-side partial / night

| Item | Notes |
|------|-------|
| mutmut full re-run ≥75% | Baseline 73%; killers green; night job |
| Backup restore prod | dry-run WORK; prod HOLD |
| RLS live sample | doc sample; prod HOLD |
| MEMORY consolidada G7 | lesson index start W27; full end-wave open |

Canonical checklists: `.harness/SUI_CHECKLIST.md`, `docs/G7_SUI_WAVE14_CHECKLIST.md`, `docs/DNS_TRAEFIK_SUI_PACK_G7.md`.

---

## 7. How to create the tag when ready

**Prerequisites (Gustavo):**

1. Review this file + `docs/MVP_CUTLINE_G7.md`.
2. Optionally wait for mutmut night ≥75% and/or first WA real message — product decision.
3. Clean working tree on the commit you want to mark (prefer `master` after review).
4. `make qa` green on that commit (or known green SHA).

**Commands (only after explicit approval):**

```bash
# from repo root, on the approved commit
git status   # clean
git log -1   # confirm SHA

# annotated tag
git tag -a v0.7.0-g7-mvp -m "v0.7.0-g7-mvp — G7 Integração Total MVP cut-line (waves 13-28). Notes: docs/RELEASE_NOTES_v0.7.0-g7-mvp.md. Tag by Gustavo Almeida."

# verify
git show v0.7.0-g7-mvp --no-patch

# push tag only when ready for remote
git push origin v0.7.0-g7-mvp
```

**Do not:**

- Auto-tag from agents.
- Force-push tags.
- Tag a dirty tree with uncommitted secrets.

**Rollback tag (if created by mistake):**

```bash
git tag -d v0.7.0-g7-mvp
git push origin :refs/tags/v0.7.0-g7-mvp   # only if already pushed
```

---

## 8. Suggested commit / PR blurb

```
docs: release notes v0.7.0-g7-mvp + mutmut Wave28 report

- docs/RELEASE_NOTES_v0.7.0-g7-mvp.md (tag HOLD)
- docs/MUTMUT_REPORT_G7_WAVE28.md (killers green, baseline 73%)
- SUPER_PLANO G7.02.T1 + G7.25.T4 Wave28

Modified by Gustavo Almeida
```

---

## 9. Related docs

| Doc | Why |
|-----|-----|
| `SUPER_PLANO_G7_100_TASKS.md` | 100-task board |
| `SUPER_GOALS_G7.md` | North star + goals % |
| `docs/MVP_CUTLINE_G7.md` | Product cut-line |
| `docs/MUTMUT_REPORT_G6.md` | Mutmut baseline 73% |
| `docs/MUTMUT_REPORT_G7_WAVE28.md` | Mutmut W28 close |
| `docs/G7_PROGRESS_DASHBOARD.md` | Wave scorecard |
| `.harness/SUI_CHECKLIST.md` | Gustavo UI blockers |
| `docs/ARCHITECTURE.md` | C4 + ADRs |
| `CHANGELOG.md` | Rolling product changelog (if maintained) |

---

## 10. Verdict

| Item | Status |
|------|--------|
| Release notes complete | ✅ |
| Git tag created | ❌ **HOLD — Gustavo only** |
| G7.25.T4 checkbox | **[x] Wave28 notes ready, tag HOLD** |

**Modified by Gustavo Almeida — G7 Wave 28 · cartorio-dev**
