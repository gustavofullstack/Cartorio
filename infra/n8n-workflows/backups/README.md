# N8N Workflow Backups (Sprint 3 — 2026-06-29)

Backups pontuais pre-migration. Cada arquivo eh snapshot exato do N8N prod (via `GET /api/v1/workflows/{id}`).

| WF | Backup | ID prod | Migration target | Status 2026-06-29 |
|----|--------|---------|-------------------|-------------------|
| #12 | WF12_pre_mcp_2026-06-29.json | `bryQNXccPvOgNhIL` | mcpClient (already migrated) | DONE — smoke test PASS, latency <2s, executions #24294/24295/24296 SUCCESS |
| #03 | WF03_pre_chatwoot_2026-06-29.json | `00PbDJUpJlrUxAir` | @devlikeapro/n8n-nodes-chatwoot.Chatwoot | BLOCKED on credential (audit + staging spec ready) |

## Rollback

Para rollback completo:

```bash
# WF #12
curl -X DELETE -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/bryQNXccPvOgNhIL"
# Reimport
curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
  -d @infra/n8n-workflows/backups/WF12_pre_mcp_2026-06-29.json \
  "https://flow.2notasudi.com.br/api/v1/workflows"

# WF #03
curl -X DELETE -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/00PbDJUpJlrUxAir"
curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
  -d @infra/n8n-workflows/backups/WF03_pre_chatwoot_2026-06-29.json \
  "https://flow.2notasudi.com.br/api/v1/workflows"
```

## Restore ate 7 dias

Esses backups sao canonicos ate 2026-07-06. Apos isso, novo snapshot necessario (decisao produto).
