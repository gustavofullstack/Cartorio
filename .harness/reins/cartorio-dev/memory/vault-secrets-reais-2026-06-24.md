# Vault Supabase — Secrets reais aplicados 2026-06-24 19:20 BRT

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: SUCCESS** — 7 secrets atualizados de PLACEHOLDER para valores REAIS.

## TL;DR

Vault Supabase no DB `cartorio` agora tem **8 secrets com valores REAIS** (não mais placeholders). Backend pode ler via `SELECT * FROM vault.secrets WHERE name = ?`.

## Comando aplicado

```bash
# Para cada secret:
docker exec cartorio_supabase-db-1 psql -U supabase_admin -d cartorio -tA -c \
  "UPDATE vault.secrets SET secret='<value>', updated_at=NOW() WHERE name='<name>';"
```

## Erro encontrado + workaround

**Erro original**: `vault.update_secret(name, value)` espera **UUID** como primeiro argumento (não nome), retornando:
```
ERROR: invalid input syntax for type uuid: "evolution_api_key"
```

**Workaround aplicado**: usar `UPDATE vault.secrets SET secret='...' WHERE name='...'` direto (DML em vez da função).

## Secrets atualizados (verificados)

| Nome | Length | Prefix | Source |
|---|---|---|---|
| `evolution_api_url` | 33 | `https://wh` | `.env.example` (whatsapp.2notasudi.com.br) |
| `evolution_api_key` | 32 | `429683C4C9` | VPS `/etc/easypanel/projects/cartorio/api/code/.env` |
| `chatwoot_api_key` | 64 | `d22c96d044` | VPS `.env` (User token d22...) |
| `n8n_api_key` | 267 | `eyJhbGci` | VPS `.env` (JWT) |
| `opencode_go_api_key` | 67 | `sk-xcRwExj` | `.secrets/opencode-go.env` (nova key) |
| `openclaw_api_key` | 64 | `fz1qzo2xka` | VPS `OPENCLAW_GATEWAY_TOKEN` |
| `telegram_webhook_secret` | 48 | `7d68047987` | VPS `.env` |
| `cartorio_api_key_placeholder` | 72 | `J51Tu0kF2i` | VPS `.env` (CARTORIO_API_KEY) — ainda "placeholder" mas valor real |

**Total**: 8 secrets, **TODOS com valores reais** (não mais PLACEHOLDER_REPLACE_ME).

## Próximos passos

### Backend Python (FastAPI)
1. Trocar leitura de `settings.X` (Pydantic) para `SELECT secret FROM vault.secrets WHERE name = ?` em runtime
2. Cachear no Redis (TTL 1h) para não bater no DB a cada request
3. Fallback para `.env` se vault.secret não existir (backwards compat)

### Backend N8N
1. Adicionar cred `vault-supabase` (postgres connection) com `vault.read_secret()` function
2. Workflows sensíveis (audit, opt-out, LGPD) leem secrets do vault em vez de hardcoded

### Memória / Docs
1. Atualizar `.harness/reins/cartorio-dev/memory/linear-sync-2026-06-24.md` (já tem 100 tasks)
2. Marcar CAR-7 a CAR-16 (SQUAD A vault tasks) como DONE
3. Adicionar note: **NÃO rotacionar chaves** (regra Gustavo)

## Lições

1. **`vault.update_secret(name, value)` não funciona com strings** — é uma RPC que espera UUID (signature: `(secret_id uuid, new_secret text)`)
2. **Para atualizar, usar SQL direto**: `UPDATE vault.secrets SET secret=... WHERE name=...`
3. **Owner = `supabase_admin`** (não `postgres`) — toda operação precisa rodar como `supabase_admin` no DB `cartorio`
4. **Senha do `supabase_admin`** está em VPS `/etc/easypanel/projects/cartorio/api/code/.env` (NÃO em `~/.mavis/secrets/`)

## Commit

- (Vou commitar este memory agora)

Modified by Gustavo Almeida
