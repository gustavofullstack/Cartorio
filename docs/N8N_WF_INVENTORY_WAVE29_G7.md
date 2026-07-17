# N8N WF Inventory + Evolution Dual-Format — Wave 29 A2

**Date**: 2026-07-17  
**Wave**: G7 Wave 29 A2  
**Agent**: cartorio-n8n  
**Scope**: Offline validation only — no live N8N API, no secrets, no commit.

---

## 1. Offline validation status

| Check | Result |
|-------|--------|
| JSON parse of root `infra/n8n-workflows/*.json` | **PASS** (all parse) |
| Dual-format Evolution parse in backend | **PASS** (present + tested) |
| Integration / webhook catalog consistency | **PARTIAL** (catalog exists; gaps below) |
| Live N8N API inventory / active status | **HOLD-GUSTAVO** (`N8N_API_KEY` + network) |
| **Overall offline** | **PARTIAL** |

**Why PARTIAL (not FAIL):** exports parse cleanly and dual-format code is in place; full green needs live N8N reconcile + catalog gaps closed.

---

## 2. Workflow inventory (exports on disk)

**Directory**: [`infra/n8n-workflows/`](../infra/n8n-workflows/)  
**Source of truth for this wave**: offline `*.json` in **root only** (not `backups/`, not diagrams).  
**Tool**: [`scripts/n8n_wf_inventory.py`](../scripts/n8n_wf_inventory.py) (no network).

| Metric | Value |
|--------|------:|
| WF JSON files (root) | **38** |
| Broken JSON | **0** |
| INDEX.md total (auto-gen) | 38 |
| INDEX.md marked active in export | 33 |
| INDEX.md marked inactive in export | 5 |
| INDEX.md total nodes | 338 |
| Webhook-trigger WFs (INDEX) | 21 |

### 2.1 Full file list (root `*.json`)

| # | Filename | Notes (from INDEX) |
|---|----------|--------------------|
| 1 | `00-error-handler.json` | errorTrigger global |
| 2 | `01-consulta-emolumento.json` | webhook |
| 3 | `02-criar-protocolo.json` | webhook + LGPD |
| 4 | `03-handoff-human-chatwoot-v3-staging.json` | Chatwoot official node staging |
| 5 | `04-boas-vindas-lgpd.json` | consent LGPD |
| 6 | `04-consulta-protocolo.json` | webhook |
| 7 | `05-agendamento.json` | webhook |
| 8 | `06-2-via-protocolo.json` | webhook |
| 9 | `07-pesquisa-satisfacao.json` | schedule + Evolution send |
| 10 | `08-audit-verify-diario.json` | schedule audit chain |
| 11 | `10-faq-bot.json` | webhook |
| 12 | `11-monitor-cartorio.json` | webhook + schedule |
| 13 | `12-chatbot-llm-end-to-end.json` | **inactive** export; Evolution→LLM |
| 14 | `14-opencode-go-fallback.json` | **inactive** export |
| 15 | `16-prospeccao-enrichment.json` | webhook |
| 16 | `18-prospeccao-followup-d7.json` | schedule LGPD opt-out |
| 17 | `21-backup-status-5min.json` | schedule |
| 18 | `22-audit-verify-6h.json` | schedule |
| 19 | `22-mcp-server.json` | mcpTrigger |
| 20 | `23-cron-stale-detector.json` | schedule |
| 21 | `23-lgpd-esqueci-v2.json` | **inactive** export; Art. 18 |
| 22 | `24-daily-cleanup.json` | schedule |
| 23 | `24-retencao-diaria.json` | schedule LGPD retenção |
| 24 | `25-metrics-collector.json` | schedule |
| 25 | `25-protocolo-concluido-pdf.json` | schedule WhatsApp PDF |
| 26 | `26-alerta-critico.json` | webhook |
| 27 | `27-welcome-first-time.json` | **inactive** export |
| 28 | `28-audit-snapshot.json` | schedule |
| 29 | `29-rate-limit-reset.json` | schedule |
| 30 | `30-health-deep-check.json` | schedule |
| 31 | `31-telegram-listener.json` | webhook Telegram |
| 32 | `33-whatsapp-qr-scan-helper.json` | Evolution connection path |
| 33 | `34-metrics-collector-5min.json` | schedule |
| 34 | `35-llm-fallback-3x.json` | webhook LLM chain |
| 35 | `36-chatwoot-telegram-sync.json` | Chatwoot webhook |
| 36 | `37-agendamento-notarial-sync.json` | Google Calendar trigger |
| 37 | `38-emolumento-calculator.json` | webhook calculator |
| 38 | `evo-in.json` | **inactive** export; Evolution inbound → API |

### 2.2 Non-JSON siblings (not counted as WFs)

- `11_monitor_cartorio.js`, `11_monitor_cartorio_README.md`
- `INDEX.md`, `README.md`, `CHANGELOG.md`, `VALIDATION_REPORT.md`, runbooks, diagrams
- `backups/` (legacy + kiss-g7 snapshots — **excluded** from count)

### 2.3 Prior validation note (stale vs disk)

[`infra/n8n-workflows/VALIDATION_REPORT.md`](../infra/n8n-workflows/VALIDATION_REPORT.md) (2026-07-16) listed **33** WFs and a **DUPLICATE_WEBHOOK** on `lgpd-esqueci-fix.json`. That file is **not** in root today (lives under `backups/kiss-g7-2026-07-17/`). Re-run `python3 scripts/n8n_workflow_validator.py` after any re-import of backup copies into root.

---

## 3. Evolution dual-format evidence

AGENTS.md requirement: accept **both** root-level `payload.message` **and** nested `payload.data.message`.

### 3.1 Present — primary parsers

| Location | Lines | Role |
|----------|-------|------|
| [`backend/app/api/v1/whatsapp.py`](../backend/app/api/v1/whatsapp.py) `parse_evolution_payload` | **302–376** | Explicit dual-format: nested `data.message`/`data.key` **or** root `message`/`key`; tags `format: nested|root` |
| [`backend/app/api/v1/router.py`](../backend/app/api/v1/router.py) `_parse_dual_format` | **872–897** | Health helper: nested message else root `message` |
| [`backend/app/api/v1/router.py`](../backend/app/api/v1/router.py) `webhook_evolution_health` | **900–943** | GET `/webhook/evolution/health` — simulates legado + moderno |
| [`backend/app/api/v1/router.py`](../backend/app/api/v1/router.py) `webhook_evolution` | **997–1012** | POST path: `_data.get("message")` else `payload.get("message")`; sender from nested key else root |

**Snippet evidence** (`whatsapp.py`):

```python
# Dual-format: nested data.* OU root-level (G7.04.T3)
_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
...
if not _message:
    _message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
...
"format": "nested" if payload.get("data") else "root",
```

**Snippet evidence** (`router.py` webhook body):

```python
_msg = (
    _data.get("message")
    if (_data and isinstance(_data, dict))
    else (payload.get("message") or {})
)
```

### 3.2 Tests still covering dual-format

| File | Coverage |
|------|----------|
| [`backend/tests/test_g7_wave17_integration.py`](../backend/tests/test_g7_wave17_integration.py) | `TestEvolutionDualFormat` + Hypothesis nested/root (G7.04.T3) |
| [`backend/tests/test_evolution_health.py`](../backend/tests/test_evolution_health.py) | asserts `dual_format_parse == "healthy"` |

### 3.3 Nested-only path (documented gap, not dual-format regression)

[`backend/app/services/evolution_ingest.py`](../backend/app/services/evolution_ingest.py) **L100–105** requires `payload["data"]` dict; rejects `missing_data`. Used for **idempotency ingest** on modern payloads with `data.key.id`. Legacy root-level falls through to inline dual-format in `webhook_evolution` (router). This split is intentional (Sprint 2 comment in router) — dual-format remains on the public webhook surface.

### 3.4 N8N side

- `evo-in.json` POSTs body to `https://api.2notasudi.com.br/api/v1/webhook/evolution` (backend owns dual-format).
- Export marked **inactive** in INDEX — live activation is HOLD-GUSTAVO.

---

## 4. Webhook catalog / integration matrix

### 4.1 Docs that mention webhooks

| Doc | What it covers | Gap |
|-----|----------------|-----|
| [`docs/INTEGRATION_MATRIX_G7.md`](INTEGRATION_MATRIX_G7.md) | C4: Telegram + Evolution dual-fmt → FastAPI; N8N 34+ WFs; rows Telegram/Evolution webhook status | Counts **34+** vs disk **38**; no per-path webhook catalog; live status stale (Wave 15/16 radar) |
| [`docs/API_ENDPOINTS_CATALOG.md`](API_ENDPOINTS_CATALOG.md) | POST `/webhook/chatwoot`, POST `/webhook/evolution`; GET evolution health; POST telegram webhook | Missing dual-format note; no N8N intermediate paths (`evo-in`, WF webhook paths); Telegram listed under Health block not only Webhooks |
| [`docs/API.md`](API.md) | Webhooks table + EVO-IN mention | Header still says “16 N8N workflows” (stale vs 38) |
| [`infra/n8n-workflows/INDEX.md`](../infra/n8n-workflows/INDEX.md) | Per-WF trigger types | Not linked from INTEGRATION_MATRIX |
| [`docs/CANAL_HEALTH_MATRIX.md`](CANAL_HEALTH_MATRIX.md) | Webhooks line: dual-format + HMAC | Canal health live-dependent |

### 4.2 Catalog gaps (offline)

1. **INTEGRATION_MATRIX** WF count **34+** ≠ **38** exports on disk.  
2. **No single matrix** of N8N webhook paths ↔ FastAPI endpoints ↔ channel.  
3. **API.md** intro still **16 workflows**.  
4. **API_ENDPOINTS_CATALOG** omits dual-format / legacy note on Evolution POST.  
5. **Live active vs export `active` flag** unknown without N8N API.

---

## 5. HOLD-GUSTAVO

| Item | Why |
|------|-----|
| `N8N_API_KEY` + reachable N8N base URL | Live list/activate/export (`make n8n-list`, `make n8n-export`, `check_all_workflows.sh`) |
| Reconcile live WFs vs 38 disk exports | Drift risk after kiss/backup moves |
| Activate/deactivate policy for 5 inactive exports (`12`, `14`, `23-lgpd`, `27`, `evo-in`) | Product/HITL decision |
| Evolution instance QR / 502 path (matrix 🔴) | Infra, not offline JSON |
| Telegram webhook secret / token HOLD | Canal matrix |
| Re-run `n8n_workflow_validator.py` after any backup JSON re-imported to root | Prior DUPLICATE_WEBHOOK on `lgpd-esqueci` |

**Do not** put real keys in git or in this report.

---

## 6. How to re-run offline

```bash
# From repo root — no network, no secrets
python3 scripts/n8n_wf_inventory.py
python3 scripts/n8n_wf_inventory.py --json

# Optional quality rules (still offline filesystem)
python3 scripts/n8n_workflow_validator.py

# Live (HOLD — needs N8N_API_KEY)
# make n8n-list
# make n8n-export
```

---

## 7. Deliverables this wave

| Artifact | Path |
|----------|------|
| This report | `docs/N8N_WF_INVENTORY_WAVE29_G7.md` |
| Offline inventory script | `scripts/n8n_wf_inventory.py` |

---

## 8. Summary

- **38** workflow JSON exports, **0** broken JSON (offline).  
- **Dual-format Evolution parse still present** in `whatsapp.py` + `router.py` with Wave 17 tests.  
- Catalog/matrix **stale counts** and missing N8N path map → overall **PARTIAL**.  
- Live N8N API work remains **HOLD-GUSTAVO**.

**Modified by Gustavo Almeida**
