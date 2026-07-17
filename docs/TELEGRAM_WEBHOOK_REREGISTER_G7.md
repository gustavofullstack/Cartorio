# Telegram BotFather + Webhook Re-register (G7.03.T1)

**Status:** HOLD-GUSTAVO (token revogado / Lesson 178)  
**Bot (exemplo):** @TestCartorioBot ou bot de produção do cartório  
**Webhook canônico:** `https://api.2notasudi.com.br/api/v1/telegram/webhook`

---

## Pré-requisitos

1. Token novo do **@BotFather** (`/token` ou `/revoke` + novo)
2. Secret token forte: `openssl rand -hex 32`
3. Env API (Easypanel):
   - `TELEGRAM_BOT_TOKEN=<novo>`
   - `TELEGRAM_WEBHOOK_SECRET=<mesmo secret_token do setWebhook>`
4. API pública UP (`curl https://api.2notasudi.com.br/health` → 200)

---

## Passos (ordem)

### 1. Atualizar env e redeploy API
Easypanel → cartorio_api → env → redeploy (token e secret **antes** do setWebhook).

### 2. Registrar webhook

```bash
# NUNCA commitar o TOKEN. Export local only:
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_WEBHOOK_SECRET='...'   # mesmo valor no backend

# Helper (imprime curls sem echo do token no git):
python3 scripts/telegram_set_webhook.py --dry-run

# Executar de verdade:
python3 scripts/telegram_set_webhook.py --apply
```

Equivalente manual:

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://api.2notasudi.com.br/api/v1/telegram/webhook" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}" \
  -d "allowed_updates=[\"message\",\"callback_query\",\"my_chat_member\"]" \
  -d "drop_pending_updates=true"
```

### 3. Validar

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
# url correta, pending_update_count ok, last_error_message null

curl -sS https://api.2notasudi.com.br/api/v1/telegram/health
# ou GET /api/v1/telegram/webhook/info com X-API-Key
```

### 4. Smoke humano
Enviar `/start` no bot → resposta do CartórioBot (sem 502).

---

## Gotchas

| Problema | Fix |
|----------|-----|
| `parse_mode=HTML` + tags think | G7.03.T3: plain text only |
| Group migration `my_chat_member` | handler + allowed_updates (Lesson 152) |
| Secret mismatch | backend e setWebhook devem usar o **mesmo** secret |
| Token no git | `scripts/secrets_scan.py` + pre-commit |

---

## Cross-refs

- Lesson 152, 160, 178 · `docs/platforms/TELEGRAM_BOT.md` · `docs/GUIA_TESTES_TELEGRAM.md`

**Modified by Gustavo Almeida — G7 Wave 21**
