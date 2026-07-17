# Lesson 207 — G7 Wave 28 A4: SUI one-pager packs (2026-07-17)

Type: project + reference  
Agents: cartorio-n8n / evolution hybrid  

## Mission

Upgrade SUI partials with **production-ready one-pagers** without executing live QR/DNS/SSH.  
Keep SUPER_PLANO markers **[~]** until Gustavo proves live.

## Tasks

| ID | Result |
|----|--------|
| G7.04.T4 | Live SUI one-pager WA→emolumento; synthetic path already Wave22 (`test_wa_emolumento_synthetic_flow`, 156.40) |
| G7.05.T1 | Consolidated master Chatwoot go-live (DNS + Traefik merge links) |
| G7.05.T3 | Same master: WF3 handoff + labels LGPD (`lgpd`, `hitl`, `protocolo`, `emolumento`, …) |
| G7.06.T3 | OpenClaw cartorio-bot deploy steps from JSON/E6/LobeChat docs |
| G7.11.T1 | Validation sheet after restore (RESTORE_G7 remains source of procedure) |
| G7.11.T2 | Radar SSH + Tailscale TCP:22 curl/jq pass criteria |

## Artefatos

- `docs/WA_EMOLUMENTO_LIVE_SUI_G7.md`
- `docs/CHATWOOT_GO_LIVE_SUI_G7.md`
- `docs/OPENCLAW_CARTORIO_BOT_DEPLOY_G7.md`
- `docs/TAILSCALE_SSH_RADAR_LIVE_G7.md`
- `SUPER_PLANO_G7_100_TASKS.md` — partial notes → **Wave28 SUI pack refreshed**
- este lesson

## Regras

1. **Não** promover `[~]` → `[x]` sem evidência live (msg WA, dig DNS, agents.list, radar ssh up).  
2. Secrets só via env (`EVOLUTION_API_KEY`, operator token) — não re-commit keys de guias legados.  
3. HITL + PII scrub permanecem P0 em handoff Chatwoot e tools OpenClaw.  
4. Tailscale down ≠ P0 se API pública/EasyPanel OK (Lesson 176).  
5. Cross-refs: RESTORE_G7 (procedimento) vs SSH_RADAR_LIVE (validação pós).

## Validação agent-side

```bash
test -f docs/WA_EMOLUMENTO_LIVE_SUI_G7.md
test -f docs/CHATWOOT_GO_LIVE_SUI_G7.md
test -f docs/OPENCLAW_CARTORIO_BOT_DEPLOY_G7.md
test -f docs/TAILSCALE_SSH_RADAR_LIVE_G7.md
cd backend && uv run pytest -q --no-cov \
  tests/test_g7_wave22_integration.py::test_wa_emolumento_synthetic_flow
```

## Notas

- Wave28 = doc pack only for residual SUI-heavy partials (n8n/evolution/sre).  
- Chatwoot master **linka** DNS_TRAEFIK, TRAEFIK_ROUTERS_MERGE, HANDOFF, AGENT_BOT — evita fork de runbooks.  
- OpenClaw deploy reforça Lesson 177 scopes `operator.read|write`.  
- Stamp textual nos partials: **Wave28 SUI pack refreshed**.

**Modified by Gustavo Almeida — G7 Wave28**
