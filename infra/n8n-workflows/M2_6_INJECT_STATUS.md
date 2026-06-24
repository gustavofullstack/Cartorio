# M2.6 — feat:variables Workaround (Partial)

**Date**: 2026-06-24 10:40 BRT
**Owner**: cartorio-n8n (reun) — session `mvs_3fb892d492d7489caf3c78f1e621ea6d`
**Status**: **PARTIAL — 2/7 envs injected, 5/7 BLOCKED (empty values)**

## Summary

N8N community license não inclui `feat:variables`. Workaround: injetar env vars customizadas no service spec do container `cartorio_n8n` via `docker service update --env-add`. Restart automático (~30-60s downtime aceitável).

## Audit Pre-M2.6 (2026-06-24 13:36 BRT)

`docker service inspect cartorio_n8n` mostra **21 env vars**, todas default (DB_*, N8N_ENCRYPTION_KEY, N8N_RUNNERS_*, WEBHOOK_URL, N8N_HOST, N8N_PROTOCOL, EXECUTIONS_DATA_PRUNE, N8N_PROXY_HOPS, N8N_COMMUNITY_PACKAGES, N8N_UNVERIFIED_PACKAGES_ENABLED). **ZERO env customizadas** — confirmação do root cause dos 7 cron workflows broken.

## Env Injection Status

| # | Key | Value | Source | Status |
|---|-----|-------|--------|--------|
| 1 | `EVOLUTION_API_URL` | `http://cartorio_evolution-api:8080` | cartorio_api container env | ✅ **INJECTED** |
| 2 | `EVOLUTION_API_KEY` | `429683C4C977415CAAFCCE10F7D57E11` | cartorio_api container env | ✅ **INJECTED** |
| 3 | `CARTORIO_API_KEY` | (empty) | n/a | ❌ **BLOCKED** — value not in any container, .env, or backend code |
| 4 | `CHATWOOT_BOT_TOKEN` | (empty) | `backend/.env.example`: `PENDING_GUSTAVO_UI` | ❌ **BLOCKED** — needs Gustavo UI |
| 5 | `TELEGRAM_BOT_TOKEN` | (not configured) | n/a | ❌ **BLOCKED** — value doesn't exist anywhere |
| 6 | `SUPABASE_ANON_KEY` | (empty) | cartorio_api container env: empty | ❌ **BLOCKED** — value not configured |
| 7 | `SUPABASE_SERVICE_ROLE_KEY` | (empty) | cartorio_api container env: empty | ❌ **BLOCKED** — value not configured |

## Risk Mitigation

Backup created at `/tmp/n8n-backup-1782308402.json` (before first inject). Rollback path: `docker service rollback cartorio_n8n` (reverts to previous service spec).

Restart time observed: ~30s per `--env-add`, ~60s total for 2 injects. Service `cartorio_n8n converged` confirmed after each.

## Critical Side-Finding (BLOCKER para Sprint 3)

**`DB_POSTGRESDB_HOST=db`** — N8N currently uses compose alias `db` which does NOT resolve in Swarm mode (per ADR-010: DB_HOST em Swarm = IP direto do container do banco, NUNCA alias DNS). Esta é a razão pela qual N8N pode estar usando o DB errado ou com erro intermitente de conexão. **A corrigir**: `docker service update --env-add DB_POSTGRESDB_HOST=10.0.1.34` (IP direto do container Supabase DB, conforme histórico de fix aplicado em 2026-06-23 11:18 BRT — TASKS.md E1.S1.WF5-10).

Não apliquei essa correção em M2.6 porque é fora do scope (env injection é para $env.X, não para DB_HOST). Sugiro abrir P1 separado.

## Recommendation

**Próximos passos**:
1. **Gustavo GO**: criar tokens faltantes (CHATWOOT_BOT_TOKEN via UI, TELEGRAM_BOT_TOKEN via @BotFather, CARTORIO_API_KEY via `openssl rand -hex 32`, SUPABASE_ANON_KEY + SUPABASE_SERVICE_ROLE_KEY via Supabase dashboard)
2. Após tokens criados: injetar via M2.6 step 3-7
3. Workaround permanente: upgrade N8N enterprise (Variables feature) ou integrar Vault/SOPS para secrets dinâmicos (Sprint 3 M4.1)

Modified by Gustavo Almeida