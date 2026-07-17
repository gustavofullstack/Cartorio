# Lesson 209 — G7 Wave 29 closeout (orchestrator G7 + 4-agent pack)

**Type:** project + reference (cross-rein)  
**Date:** 2026-07-17  
**Agents:** A1 cartorio-dev · A2 cartorio-n8n · A3 cartorio-lgpd · A4 cartorio-sre  
**Plan:** `SUPER_PLANO_G7_100_TASKS.md` · Goals: `SUPER_GOALS_G7.md`

---

## Contexto

Gustavo: **CONTINUE!!** + integração total + super plano 100 tasks + 4 agents/squad em loop.  
Estado real pré-wave (Lesson **208**): G7 Waves 13–28 agent-side **~92% [x] / ~96% weighted**, **8 [~] SUI-only**, orquestrador `super_loop` ainda lia plano **v25** (reportava ~20/100 incorreto).

**Regra Lesson 185:** preferir 1–2 agents reais; Wave 29 usou **2 subagents paralelos** (A2/A3) + orquestrador local (A1/A4).

---

## Entregas (4 slots)

| Slot | Rein | Entrega | Path |
|------|------|---------|------|
| **A1** | dev | Super loop default **G7** (v25 = legacy) | `scripts/super_loop_orchestrator.py` · `make super-loop` · `make g7-next` |
| **A2** | n8n | Inventário offline **38** WF JSON · dual-format **PASS** | `docs/N8N_WF_INVENTORY_WAVE29_G7.md` · `scripts/n8n_wf_inventory.py` |
| **A3** | lgpd | Dashboard go-live LGPD + secrets scan docs **CLEAN** | `docs/LGPD_GO_LIVE_DASHBOARD_G7.md` |
| **A4** | sre | Canal health live (radar red, expanded 404, DNS soft 7/7) | `docs/CANAL_HEALTH_MATRIX_WAVE29_G7.md` |

### Live snapshot A4 (não inventado)

- Radar: `database/redis/openclaw/supabase` **online**; `n8n/evolution/chatwoot` **offline** → status **red**
- `/api/v1/health/radar/expanded` → **404** (redeploy SUI)
- `/health` root → **200**
- DNS soft: **7/7** core OK; **3 NXDOMAIN** chatwoot/n8n/supabase
- Composite gate: local WORK · prod **exit 2 PROD_HOLD**

### N8N A2

- 38 exports válidos · 0 JSON quebrado · 33 active / 5 inactive · 338 nodes
- Dual-format Evolution ainda em `whatsapp.py` + `router.py` (+ tests Wave 17)
- Catalog gaps: `API.md` ainda diz 16 WFs (stale); matrix diz 34+

### LGPD A3

- DPA READY_TO_SIGN · Privacy DRAFT · RIPD 1.4 · inventory 25 fields — cross-index no dashboard
- Secrets scan untracked G7 docs: **sem chaves reais** (só FP placeholders `sk-xxxx`)

---

## O que NÃO mudou (e não deve ser “flipped” agent-side)

As **8 tasks [~]** do super plano continuam partial até SUI:

1. G7.04.T4 WA real emolumento  
2. G7.05.T1 DNS chatwoot + Traefik  
3. G7.05.T3 Handoff prod  
4. G7.06.T3 OpenClaw cartorio-bot live  
5. G7.11.T1/T2 Tailscale  
6. G7.12.T1 DNS A×3  
7. G7.25.T1 SUI ticks  

**Anti-padrão evitado:** re-empacotar Wave 30 G6 ou marcar [x] sem evidência live (Lesson 206/208).

---

## Loop harness pós-fix

```bash
make g7-status          # 92 done / 8 partial
make g7-next            # 4 next SUI-facing tasks
python3 scripts/super_loop_orchestrator.py status   # G7 canônico
python3 scripts/super_loop_orchestrator.py legacy-status  # v25 histórico
python3 scripts/n8n_wf_inventory.py
make dns-check && make g7-composite
```

`.brain/loop-state.json` → `g7_wave=29`, status `g7_wave29_closeout_done_92pct_sui_hold`.

---

## Próximo (W30-SUI — humano)

Ordem mestra (lesson-206):

1. DNS A×3 Cloudflare  
2. Env DATABASE_URL Evo/CW/N8N  
3. Redeploy API (`/radar/expanded` 200) + Traefik merge  
4. Telegram token + LobeChat key + WA QR  
5. OpenClaw scopes + cartorio-bot  
6. DPA sign + Privacy publish  
7. Start 72h (`docs/STABILITY_WINDOW_72H_G7.md`)  
8. Tag `v0.7.0-g7-mvp`  
9. Mega-commit untracked G7 artifacts (se Gustavo autorizar)

---

## Cross-refs

- lesson-185 (1–2 agents) · 176 (env 502) · 179 (DNS) · 206 (consolidada) · 207 (SUI packs) · 208 (resync)

Modified by Gustavo Almeida — G7 Wave 29
