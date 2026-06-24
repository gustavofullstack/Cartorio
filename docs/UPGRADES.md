# Upgrade Roadmap — Cartorio 2 Notas Uberlandia

Atualizado: 2026-06-24. Fonte: Docker Hub / Easypanel registry.

## Status Atual vs Latest

| Servico       | Atual em Prod | Latest Disponivel | Tipo      | Downtime | Risco |
|---------------|---------------|-------------------|-----------|----------|-------|
| N8N           | 1.94.x        | 2.0+              | MAJOR     | sim      | medio |
| Evolution API | v1.8.5        | v1.8.7            | PATCH     | sim      | baixo |
| Chatwoot      | v3.x          | v4.15.1           | MAJOR     | sim      | ALTO  |
| Postgres      | 15.x          | 17.6.1            | MAJOR     | sim      | ALTO  |
| OpenClaw      | 2026.6.x      | 2026.6.10         | MINOR     | rolling  | baixo |

## Plano de Upgrade

### 1. N8N 1.94.x → 2.0+
- **Quando**: Q3/2026 (aguardar 2.x.1 com bugfixes).
- **Breaking**: novo permission system, deprecacao de `ExecuteCommand`.
- **Acao**: ler release notes; testar WFs em staging; migrar creds.
- **Downtime**: ~5min (restart container).

### 2. Evolution API v1.8.5 → v1.8.7 (PATCH)
- **Quando**: imediato (baixo risco).
- **Acao**: Easypanel → cartorio_evolution → image `v1.8.7` → redeploy.
- **Downtime**: ~30s. Rollback trivial.

### 3. Chatwoot v3.x → v4.15.1 (MAJOR — BREAKING)
- **Quando**: apos N8N 2.0 estabilizar.
- **Breaking**: API v4 (paths `/api/v4/...`), novo agent model, removido `automation_rule` v1.
- **Acao**: dump DB Chatwoot → restore em v4 → rerun migrations; validar webhooks N8N.
- **Downtime**: 30-60min. Testar com superadmin em staging.
- **Refs**: docs/EVOLUTION_API_INTEGRATION.md.

### 4. Postgres 15.x → 17.6.1 (MAJOR)
- **Quando**: apos Chatwoot v4.
- **Breaking**: replication slots format, pg_stat_* removidos.
- **Acao**: `pg_dumpall` → novo container `postgres:17.6.1` → restore → repoint `DATABASE_URL` em todos os 15 services Supabase + cartorio-api + evolution + n8n.
- **Downtime**: 1-2h (janela sabado 02:00 BRT). Backup triplo antes.
- **Cuidado**: Supabase gerencia migrations internas; coordinate upgrade com Supabase release.

### 5. OpenClaw 2026.6.x → 2026.6.10 (MINOR)
- **Quando**: rolling, sem janela.
- **Acao**: `docker service update --image ... cartorio_openclaw-gateway`.
- **Versao no env**: `OPENCLAW_VERSION=2026.6.10`.

## Pre-flight Checklist (qualquer upgrade MAJOR)
- [ ] Backup completo: `pg_dumpall` + `redis-cli BGSAVE` + `.env` archive.
- [ ] Snapshot VPS via Easypanel (volume freeze).
- [ ] Notificar usuarios (banner no Chatwoot).
- [ ] Smoke test post-upgrade: `/health`, `/mcp-servers`, `/docs`.
- [ ] Rollback plan documentado (imagem anterior taggeada).
