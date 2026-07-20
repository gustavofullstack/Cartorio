# RUNBOOK

Runbook operacional resumido (2026-07-20). Detalhes por tema em `operations/`.

## Acessos (sempre bounded)

```bash
ssh -o ConnectTimeout=8 -o BatchMode=yes vps-public 'docker service ls'          # 19 serviços 1/1
ssh -o ConnectTimeout=8 -o BatchMode=yes vps-public 'docker service logs cartorio_api --tail 50'
ssh -o ConnectTimeout=8 -o BatchMode=yes pc-linux-local 'cd ~/Cartorio && make test-fast'
```

## Incidentes frequentes

| Sintoma | Causa provável | Ação |
|---|---|---|
| Webhook Telegram 401 | secret divergente | re-sync `POST /api/v1/telegram/set-webhook` com `X-API-Key`; nunca setWebhook sem `secret_token` |
| Bot silencia | LLM lento/slots falhos | verificar fallback chain + circuit breaker; timeout 45s/slot; checar métricas por provider |
| Chatwoot crashloop | pgvector ausente | habilitar extensão no Postgres e restart |
| Serviço não escala (host-mode) | porta em uso | scale 0 → 1 (nunca 1→1) |
| n8n 401 silencioso | auth header errado | revisar credencial do node MCP |

## Rotinas

- **Deploy**: branch → PR (`make qa` verde) → merge master → EasyPanel rebuild → smoke → probes Telegram.
- **Migration**: backup → `make -C backend alembic-up` → smoke.
- **Verificação audit**: amostra read-only da cadeia SHA256; full em janela off-hours.
- **Backup/restore**: `operations/BACKUPS.md` / `operations/RESTORE.md` (dry-run report 2026-07-16 em `docs/`).

## Proibições operacionais

- Sem rotação de chaves sem ordem do dono; sem sessão SSH interativa; sem `tail -f` sem limite; sem `print` de segredo (mascarar 4 primeiros chars + `...`).
