# Canal Health Matrix — Live Probe 2026-07-16 (G6.D.T6 Wave 13)

> **Status global: 🟡 YELLOW** — API core UP (database/redis/openclaw/supabase
> online); canais N8N / Evolution / Chatwoot DOWN ou NXDOMAIN; WhatsApp/Chat
> 502; 3 A records Cloudflare faltando (HOLD-GUSTAVO).
>
> Substitui snapshot 2026-07-14 (todos 502). Re-probe: `2026-07-16` BRT.
> Ferramentas: `make radar-smoke` · `curl /api/v1/health/radar` · dig + curl.

---

## Resumo executivo

| # | Canal | Status | HTTP / DNS | Evidência | Ação |
|---|-------|--------|------------|-----------|------|
| 1 | FastAPI `/health` | 🟢 UP | 200 | `{"status":"ok","version":"0.6.0"}` | — |
| 2 | FastAPI `/health/radar` | 🟡 RED agreg. | 200 | db/redis/openclaw/supabase online; n8n/evo/chatwoot offline | SUI env + DNS |
| 3 | FastAPI `/health/radar/expanded` | 🔴 NOT DEPLOYED | 404 | código em master, imagem prod antiga | redeploy API |
| 4 | OpenClaw / agent | 🟢 UP | 200 | `agent.2notasudi.com.br` | cartorio-bot E8 HOLD |
| 5 | EasyPanel | 🟢 UP | 200 | `easypanel.2notasudi.com.br` | — |
| 6 | N8N flow | 🟡 DEGRADED | 404 | `flow.2notasudi.com.br` TLS OK, path `/` 404 | healthz path / service |
| 7 | WhatsApp Evolution | 🔴 DOWN | 502 | `whatsapp.2notasudi.com.br` | DATABASE_URL + QR |
| 8 | Chatwoot chat | 🔴 DOWN | 502 | `chat.2notasudi.com.br` | DATABASE_URL + restart |
| 9 | Supabase (typo) | 🟡 DEGRADED | 404 | `supbase.2notasudi.com.br` resolve | path/service |
| 10 | DNS `chatwoot.*` | 🔴 NXDOMAIN | 000 | sem A record Cloudflare | SUI Gustavo ~2min |
| 11 | DNS `n8n.*` | 🔴 NXDOMAIN | 000 | sem A record Cloudflare | SUI Gustavo ~2min |
| 12 | DNS `supabase.*` | 🔴 NXDOMAIN | 000 | sem A record (typo `supbase` em uso) | decisão B5 |

**Radar API (live):**
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

## Integrações transversais (stack completo pedido)

| Camada | Componente | Estado local/repo | Estado prod |
|---|---|---|---|
| API | FastAPI + OpenAPI/Swagger | ✅ 2994+ tests | 🟢 UP v0.6.0 |
| WebSocket | `/ws/atendimentos` | ✅ tests | 🟢 via API |
| Webhooks | Telegram / Evolution / Chatwoot | ✅ dual-format + HMAC | 🟡 parcial |
| Postgres | Supabase self-hosted | ✅ Alembic | 🟢 online |
| Redis | idempotência + rate limit | ✅ | 🟢 online |
| MCP | `mcp_server.py` 13 tools | ✅ | depende mount |
| Brain | `.brain/` + BRAIN router | ✅ | ✅ |
| Harness | 9 reins + loop-engineer | ✅ G6 waves 1-13 | — |
| Postman | `docs/postman_collection.json` | ✅ | — |
| Tailscale | 100.99.172.84 | docs | 🔴 offline 2d+ (Lesson 176) |
| Proxy/DNS | Traefik + Cloudflare | runbooks | 🟡 3 NXDOMAIN |
| OpenClaw agent | cartorio-bot | spec E6 + E2E scaffold | HOLD deploy |
| LobeChat | agent UI | CORS fix Lesson 170 | 🟢 HTTP / key HOLD |
| Skills | `.agents/skills/*` | 12+ skills | — |
| CI/CD | GitHub Actions matrix 3.12+3.13 | ✅ | ✅ |
| Observability | Prometheus + AlertManager + Loki | ✅ yml | deploy HOLD |

---

## SUI — Só Gustavo Resolve (ordem sugerida ~45min)

1. **Cloudflare DNS** — 3 A records: `chatwoot`, `n8n`, `supabase` → `187.77.236.77` (proxy ON)  
   Runbook: `infra/dns/CLOUDFLARE_RUNBOOK.md`
2. **Easypanel env** — `DATABASE_URL` correta em evolution / chatwoot / n8n (Lesson 176)
3. **Redeploy API** — publicar `/api/v1/health/radar/expanded` (já em master)
4. **Telegram** — regenerar token BotFather + webhook
5. **LobeChat** — `OPENAI_API_KEY` real (não `sk-xxxx`)
6. **WhatsApp QR** — `whatsapp.2notasudi.com.br/manager`
7. **OpenClaw E8** — operator token + `cartorio-bot` no openclaw.json
8. **AlertManager + Loki** — copiar yml VPS + restart stack

---

## Como revalidar (super teste validador)

```bash
# Radar classico + fallback expanded
make radar-smoke

# 10 dominios DNS
make dns-check || bash scripts/check_dns_health.sh

# Gates locais
make lint && make test-fast

# Suite G6
make openapi-check n8n-validate coverage-gate
```

---

**Modified by Gustavo Almeida + cartorio-sre — G6 Wave 13 (2026-07-16)**
