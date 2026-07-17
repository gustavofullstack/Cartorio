# Redeploy `/radar/expanded` prod (G7.18.T1)

**Status:** `[x] Wave27` code verified + runbook — **prod redeploy = SUI**  
**Endpoint:** `GET /api/v1/health/radar/expanded`  
**Code:** `backend/app/api/v1/health_radar_expanded.py` (montado em `app/main.py`)  
**Tests:** `backend/tests/test_health_radar_expanded.py` (+ OpenAPI assert em `test_g7_lobechat_openclaw_intents.py`)  
**Date:** 2026-07-17  

---

## Por que redeploy?

| Ambiente | Estado típico |
|----------|----------------|
| Master / local | Endpoint **presente** (OpenAPI + pytest) |
| Produção (imagem antiga) | Frequentemente **404** — feature F6 não publicada |

Gap documentado em: `docs/CANAL_HEALTH_MATRIX.md`, `docs/DNS_TRAEFIK_SUI_PACK_G7.md`, `docs/CD_EASYPANEL_HOOK_G7.md`.

---

## Verificação local (agent — já verde)

```bash
# Router importado no main
rg 'health_radar_expanded|expanded_router' backend/app/main.py

# OpenAPI path
cd backend && uv run python -c "
from app.main import app
paths = app.openapi()['paths']
assert '/api/v1/health/radar/expanded' in paths
print('OK openapi radar/expanded')
"

# Testes unitários (checks mocked)
uv run pytest -q --no-cov tests/test_health_radar_expanded.py
```

Categorias do expanded: `health`, `dns`, `traefik`, `ssh`, `tailscale`, `disk`.  
Agregação: green / yellow / red (fail-open por check; red se DB/Redis críticos down).

---

## Redeploy EasyPanel / Swarm (SUI Gustavo) — ~5–10 min

### Opção A — EasyPanel UI

1. Abrir `https://easypanel.2notasudi.com.br` → projeto **cartorio** → serviço **api**.  
2. Deploy / Rebuild a partir da branch `master` (imagem com `health_radar_expanded`).  
3. Aguardar task running 1/1.  
4. Se publish mode **host** e porta travada: scale **0 → 1** (não 1→1).  

### Opção B — Swarm CLI (SSH/Tailscale)

```bash
# Força nova task (se image tag latest já pushada)
docker service update --force cartorio_api

# Se porta host stuck
docker service scale cartorio_api=0
sleep 5
docker service scale cartorio_api=1

# Logs
docker service ps cartorio_api
docker service logs --tail 80 cartorio_api
```

### Opção C — CD hook documentado

Ver `docs/CD_EASYPANEL_HOOK_G7.md` (webhook / deploy hook se configurado).

---

## Validação pós-redeploy

```bash
# 1) Liveness
curl -fsS -o /dev/null -w 'health %{http_code}\n' https://api.2notasudi.com.br/health

# 2) Radar classic
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool | head

# 3) Radar expanded — meta: 200 (não 404)
curl -sS -o /dev/null -w 'radar/expanded %{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded

# 4) Corpo JSON (categorias)
curl -sS https://api.2notasudi.com.br/api/v1/health/radar/expanded \
  | python3 -m json.tool | head -80

# 5) Makefile smoke (raiz)
make radar-smoke
# ou: make -C backend smoke
```

### Esperado

| Check | OK | HOLD / fail |
|-------|----|-------------|
| HTTP code | **200** | 404 = imagem sem feature; 502 = Traefik/upstream |
| JSON | `status` green\|yellow\|red + categorias | body vazio / HTML EasyPanel |
| DNS category | hosts com status | NXDOMAIN chatwoot/n8n até G7.12 |
| Tailscale/SSH | up ou warn | yellow se TS offline (Lesson 176/11) |

Script: `scripts/radar_smoke.py` (tolera 404 com note de redeploy).

---

## Rollback

- Re-deploy imagem anterior (tag pin no EasyPanel).  
- Expanded é **somente leitura** — rollback não afeta dados; só remove o path se imagem antiga.  
- Radar classic `/api/v1/health/radar` permanece como fallback.

---

## Cross-refs

| Doc | Relação |
|-----|---------|
| `docs/platforms/API_HEALTH_RADAR.md` | Spec categorias + alerting |
| `docs/CD_EASYPANEL_HOOK_G7.md` | §5.1 ordem mínima curl |
| `docs/G7_SUI_WAVE14_CHECKLIST.md` | Item 3 redeploy |
| `docs/TAILSCALE_RESTORE_G7.md` | Checks ssh/tailscale no expanded |
| `Makefile` | `radar-smoke` target |

---

## Definition of Done

- [x] Código + OpenAPI + testes locais  
- [x] Runbook EasyPanel + curl  
- [ ] Prod HTTP 200 (SUI)  
- [ ] `make radar-smoke` green em prod  

**Modified by Gustavo Almeida — G7 Wave 27**
