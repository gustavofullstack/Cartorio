# Supabase Cron + Vault — 2026-06-24 18:55 BRT

> Sessão: 1 Explore agent (TRY 4) + ZCode orquestrador.
> **Resultado: SUCESSO** após 3 tentativas anteriores.

## Resultado Final

**5 cron jobs + 8 vault secrets** criados em prod.

### Cron jobs (DB `postgres`, jobid 1-5)
| ID | Nome | Schedule | Comando |
|---|---|---|---|
| 1 | cleanup-sessions-24h | `0 3 * * *` | DELETE chat_hub_sessions > 24h |
| 2 | audit-chain-verify-6h | `0 */6 * * *` | COUNT audit_log sem HMAC |
| 3 | retention-daily-03h | `0 3 * * *` | DELETE audit_log > 365d |
| 4 | stale-detector-5min | `*/5 * * * *` | UPDATE webhook_event_dlq attempts |
| 5 | dlq-refresh-10min | `*/10 * * * *` | COUNT webhook_event_dlq |

**Nota**: pg_cron roda no DB `postgres` (config `cron.database_name`) por limitação do Supabase custom image. Jobs fazem queries cross-DB via dblink quando necessário.

### Vault secrets (DB `cartorio`, 8 secrets)
- `evolution_api_url`, `evolution_api_key`
- `chatwoot_api_key`
- `n8n_api_key`
- `opencode_go_api_key`
- `openclaw_api_key`
- `telegram_webhook_secret`
- `cartorio_api_key_placeholder` ⚠️ (valor placeholder — substituir depois)

## Tentativas anteriores (lições)

1. **TRY 1**: `psql -U postgres -d cartorio -c "CREATE EXTENSION pg_cron"` → ERRO "can only create extension in database postgres" (cartorio DB não é cron.database_name)
2. **TRY 2**: `dblink` com password → ERRO "password is required" (server não pede senha)
3. **TRY 3**: GRANT + ALTER OWNER → ERRO "must be owner of database cartorio" (postgres não é owner)
4. **TRY 4 (SUCESSO)**: Conectar como **`supabase_admin`** (owner real do DB) → funcionou! `CREATE EXTENSION pg_net; CREATE EXTENSION supabase_vault;` direto no cartorio DB.

## Decisões técnicas

- **pg_cron SEMPRE no DB postgres** (limitação do worker)
- **Vault secrets no DB cartorio** (onde o backend lê via PostgREST)
- **dblink para jobs cross-DB** (quando precisa)
- **PLACEHOLDER_REPLACE_ME** para secrets sem valor real — substituir via `SELECT vault.update_secret(name, value)` quando necessário

## Arquivo

`/Users/gustavoalmeida/projetos/Cartorio/infra/supabase/migrations/2026_06_24_0002-supabase-cron-vault-final.sql` (4861 bytes, 106 linhas)

## Commit
`efab104912d7d9467f38e0a10425d24272eddc27`
`feat(supabase): cron jobs + vault secrets via supabase_admin (TRY 4 success)`

## Próximos passos

1. Substituir 7 placeholders por valores reais via `vault.update_secret()`
2. Backend: ler secrets via `SELECT * FROM vault.secrets WHERE name = ?` (não mais do .env)
3. Validar que os 5 cron jobs rodaram pelo menos 1x cada (em 24h, 5min, 10min, 6h, 3h)
4. Adicionar cron job para **auto-restart OpenClaw** se cair (pq tá em restart loop silencioso)

## Telegram bot E2E test (workflow 31)

- `POST /webhook/telegram-cartoriobot` com `/start` → HTTP 200 em 9.96s
- Bot `@test_cartorio_bot` ativo, `getMe` 200 OK
- **Falha no último node "Audit chain verify"** → "Method not allowed" (precisa GET, tá mandando POST)
- **Solução**: corrigir node no N8N UI (não via API)

## OpenClaw M3 fix summary

- 4 config files editados (openclaw.json x2, agent.json, agent/models.json)
- 4 backups automáticos criados
- **M3 (1M context) + temperature=0** aplicado
- **Thinking: enabled=true**
- **Provider: openai/opencode-go** (substituiu codex/gpt-5.5 que dava 401)
- **/v1/chat/completions**: 404 persistente — formato `gateway.http.endpoints.chatCompletions` rejeitado por OpenClaw 2026.6.10 (revertido)
- **WS endpoints**: funcionando (chat.metadata 407ms OK)

Modified by Gustavo Almeida
