# CANAL HEALTH MATRIX — G7 Wave 29 A4 (live probe)

**Data:** 2026-07-17 · **Agent:** cartorio-sre (Wave 29 A4)  
**Composite gate:** `PROD_HOLD` exit **2** (local WORK · DNS soft WORK · radar HOLD)  
**DNS soft:** core **7/7 OK** · optional **3 NXDOMAIN HOLD** (chatwoot / n8n / supabase)

> Snapshot agent-side. Produção green exige SUI Gustavo (DNS×3 + env + redeploy).  
> Fonte consolidada SUI: `docs/SUI_CHECKLIST_G7_WAVE28.md`.

---

## Endpoints (api.2notasudi.com.br)

| Probe | HTTP (sessão Wave 29) | Note |
|-------|----------------------|------|
| `/health` | 200 (sessões anteriores) / flaky | k8s alias; se 404 = build sem aliases root |
| `/api/v1/health` | 404 observado | path canônico pode ser `/health` ou radar |
| `/api/v1/health/radar` | **200** status=`red` | 4 online / 3 offline |
| `/api/v1/health/radar/expanded` | **404** | redeploy API HOLD — `docs/RADAR_EXPANDED_REDEPLOY_G7.md` |
| `/metrics` | 200 típico | Prometheus |

### Radar classic (JSON live revalidado Wave 29)

```json
{
  "status": "red",
  "services": {
    "database": "online",
    "redis": "online",
    "n8n": "offline",
    "openclaw": "online",
    "evolution": "offline",
    "chatwoot": "offline",
    "supabase": "online"
  }
}
```

---

## DNS soft (`make dns-check`)

| Host | Result |
|------|--------|
| api / flow / whatsapp / chat / agent / supbase / easypanel | **OK** → 187.77.236.77 |
| chatwoot.2notasudi.com.br | **NXDOMAIN HOLD** |
| n8n.2notasudi.com.br | **NXDOMAIN HOLD** |
| supabase.2notasudi.com.br | **NXDOMAIN HOLD** |

Runbook: `infra/dns/CLOUDFLARE_RUNBOOK.md` · snapshot: `docs/DNS_A_RECORDS_WAVE28_G7.md`

---

## Interpretação por canal

| Canal | Status live | Blocker SUI |
|-------|-------------|-------------|
| API + Postgres + Redis + Supabase | online (radar) | — |
| OpenClaw | online | operator scopes + `cartorio-bot` create |
| N8N | offline | DNS `n8n` + env DATABASE_URL (Lesson 176) |
| Evolution | offline | DATABASE_URL + QR |
| Chatwoot | offline | DNS `chatwoot` + env + Traefik merge |
| Telegram | N/A no radar | BotFather token revogado |
| LobeChat | DNS agent OK | `OPENAI_API_KEY` real |
| Tailscale | fora do radar público | restore admin path |
| `/radar/expanded` | 404 | redeploy API com código expandido |

---

## Composite gate (Wave 29 re-run)

```
G7 Composite Gate — PROD_HOLD (exit 2)
  [WORK] quick_import (tier=local)
  [WORK] dns (tier=prod) soft
  [HOLD] radar (tier=prod) status=red
```

Local quality gates (Lesson 208 baseline): ruff 0 · mypy 0 · pytest 3176+.

---

## DoD Wave 29 A4

- [x] Live probe snapshot escrito
- [x] Composite + DNS soft revalidados
- [x] Matriz alinhada a HOLD mestra Wave 28 (lesson-206)
- [ ] Prod green 9/9 (SUI — não agent)

---

## Cross-refs

- Lesson 176 (502 env) · 179 (DNS CF) · 206 (consolidada) · 208 (resync)
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`
- `scripts/g7_composite_gate.py` · `scripts/check_dns_health.sh`

Modified by Gustavo Almeida — G7 Wave 29 A4
