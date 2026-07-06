# STATUS — Cartório 2º Notas Uberlândia (snapshot 2026-07-06 18:10 BRT)

## 🚨 DESCOBERTA v22 — N8N REMOVIDO DO SWARM

```
docker service ls | grep -i n8n
→ (vazio — não existe cartorio_n8n nem cartorio_n8n-runner)
```

**IMPACTO**: radar health reporta `n8n: offline` desde quando? Investigar.
**AÇÃO**: criar service swarm OU documentar como fora-de-scope.

## Infra PROD (7 serviços)

| Serviço | URL | HTTP | Latência | Status |
|---|---|---|---|---|
| API FastAPI | api.2notasudi.com.br | 200 | 92ms | 🟢 UP v0.6.0 |
| Flow N8N | flow.2notasudi.com.br | 404 | 113ms | 🔴 **SERVIÇO REMOVIDO** |
| WhatsApp Evolution | whatsapp.2notasudi.com.br | 200 | 389ms | 🟡 instance close |
| Chatwoot easypanel | cartorio-chatwoot.dfgdxq.easypanel.host | timeout | 8s | 🔴 Traefik issue |
| OpenClaw | agent.2notasudi.com.br | 200 | 422ms | 🟢 UP |
| Supabase | supbase.2notasudi.com.br | 404 | 98ms | 🟡 401 esperado |
| EasyPanel | easypanel.2notasudi.com.br | 200 | 191ms | 🟢 UP |

## Containers Swarm (24 ativos — N8N removido)

```
✅ cartorio_api (1/1)
✅ cartorio_anything-llm, argilla-{web,worker,elasticsearch}
✅ cartorio_chatwoot (1/1) + sidekiq (1/1)
✅ cartorio_crwal4ai (1/1) — health endpoint não responde (porta?)
✅ cartorio_evolution-api (1/1)
✅ cartorio_grafana + otel-lgtm
✅ cartorio_langfuse-{web,worker,clickhouse,minio}
✅ cartorio_litellm-app (1/1)
✅ cartorio_lobechat, open-notebook
✅ cartorio_openclaw-gateway (1/1)
✅ cartorio_redis + dbgate + rediscommander
✅ cartorio_supabase + pgweb + dbgate
✅ cartorio_zeroclaw
✅ easypanel + easypanel-traefik
❌ cartorio_n8n (REMOVIDO)
❌ cartorio_n8n-runner (REMOVIDO)
```

## Gates qualidade v22

| Gate | Status |
|---|---|
| ruff check | 🟢 0 errors |
| mypy app/ | 🟢 0 errors (122 files) |
| pytest | 🟢 1791+ passados, 28 novos v21+v22 |
| coverage | 🟢 ≥90% |

## Entregas v22 (round atual)

- ✅ DB_POOL_SIZE 10 → 25
- ✅ dist_lock.py (Redlock simplificado via Redis SET NX)
- ✅ cartorio-backup.sh real (pg_dump + cleanup 30d)
- ✅ cron `0 3 * * *` cartorio-backup.sh agendado
- ✅ infra/supabase/migrations/2026_07_06_add_matviews.sql (2 views)
- ✅ 5 tests test_dist_lock.py
- 🔴 N8N removido Swarm (ação necessária)

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 18:10 BRT
