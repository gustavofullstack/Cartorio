---
name: lesson-152-telegram-my-chat-member-group-migration
description: Telegram bot para de responder silenciosamente quando grupo e migrado de group para supergroup, ou quando bot sai/remove do grupo. Adicionar handler my_chat_member no webhook para auto-recuperacao.
type: project
created: 2026-07-08
---

# Lesson 152 — Telegram bot para de responder apos group migration ou bot leave (2026-07-08)

## Sintoma
Gustavo clicava nos botoes do bot e nada acontecia. Webhook retornava 200
mas `sendMessage` do bot nao chegava ao Telegram. Gustavo reportou "nota
0 de mil" porque o bot nao respondia.

## Root cause (3 problemas sobrepostos)
1. **Group migration**: grupo TESTE/VALIDACAO/CORRECAO (-5319980720) foi
   migrado de group para supergroup pelo Telegram. O ID antigo virou
   `migrate_to_chat_id: -1004331849032`. Gustavo continuou mandando no
   ID antigo, onde o bot nao estava mais.
2. **Bot nao adicionado ao supergroup novo**: Gustavo nao re-adicionou
   o bot. Status = "left".
3. **TELEGRAM_WEBHOOK_SECRET configurado no .env mas o setWebhook NAO
   foi feito com secret_token**: o backend passou a exigir o secret
   (return 401), mas o Telegram nao mandava. Silenciosamente, todos os
   updates do bot foram rejeitados com 401.

## Solucao implementada (commit 2026-07-08)
1. **Handler `my_chat_member`** em `backend/app/api/v1/telegram.py`:
   - Detecta quando bot entra em grupo (`status=member` ou
     `status=administrator` com `old_status=left/kicked`)
   - Envia mensagem de boas-vindas com menu + botoes inline
   - Detecta quando bot sai (`status=left/kicked`) e loga warning
2. **`classify_metric_for_status()`** helper: mapeia status
   "ok"/"partial"/"ignored"/"duplicate" para contadores in-process
   corretos em /metrics. Antes o `responses_ok` nunca incrementava.
3. **`bump_metric("commands_handled")`** em todos os comandos
   `/comando` reconhecidos.
4. **`bump_metric("scheduled_debounce")`** quando background task
   e agendada.
5. **`bump_metric("responses_ok"/"responses_failed")`** na background
   task `_process_telegram_debounce` baseado no retorno do sendMessage.
6. **`allowed_updates` no setWebhook**: adicionado `my_chat_member` a
   lista de updates que o Telegram envia pro webhook.

## Comando canonico de recuperacao apos group migration
```bash
# 1. Detectar novo ID do grupo
curl -s "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d "chat_id=$ID_ANTIGO&text=test"
# Resposta: "migrate_to_chat_id": -100XXXXXXXXXX

# 2. Reconfigurar webhook com secret
curl -s -X POST "https://api.telegram.org/bot$TOKEN/setWebhook" \
  -d "url=$TUNNEL/api/v1/telegram/webhook&secret_token=$SECRET&allowed_updates=[\"message\",\"callback_query\",\"my_chat_member\"]"

# 3. Gustavo adiciona bot manualmente ao supergroup novo
# 4. Bot entra no grupo, my_chat_member dispara handler de welcome
```

## Pre-flight checks antes de declarar "bot nao funciona"
1. `curl https://api.telegram.org/bot$TOKEN/getWebhookInfo` — confirma
   URL + pending_update_count
2. `curl /api/v1/telegram/metrics` — ver se responses_ok incrementa
3. `curl /api/v1/telegram/health` — backend UP
4. `curl /api/v1/telegram/webhook/info` — proxy para getWebhookInfo
5. Se tunnel `trycloudflare` retornar ERROR 1033: cloudflared caiu.
   Reiniciar com `nohup cloudflared tunnel --url http://localhost:8000 &`

## Metricas
- /metrics contadores: requests_total, responses_ok, responses_partial,
  responses_failed, rate_limited, scheduled_debounce, hitl_created,
  commands_handled
- Source: `bump_metric` em `telegram.py` + `classify_metric_for_status`

## Tests
- 30 testes em `test_telegram_webhook.py` (3 novos my_chat_member +
  classify_metric_for_status)
- 164 testes Telegram totais passando (160 antigos + 4 novos)

## Files tocados
- `backend/app/api/v1/telegram.py` (handler my_chat_member + metric
  helpers + bump_metrics em todos retornos)
- `backend/tests/test_telegram_webhook.py` (+3 testes)
- `backend/.env` (sem mudanca; AUDIT_HMAC_KEY ja estava correto)
- `infra/cloudflared` (rotina de restart manual via shell)

## Modified by Gustavo Almeida
