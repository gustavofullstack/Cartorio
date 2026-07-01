#!/usr/bin/env bash
# telegram_ping.sh — ping webhook produção do bot @test_cartorio_bot
# Envia /start simulado e mede latência.
# Requer TELEGRAM_BOT_TOKEN no .env.

set -u

CARTORIO="/Users/gustavoalmeida/projetos/Cartorio"
ENV="$CARTORIO/.env"
TOKEN="${TELEGRAM_BOT_TOKEN:-$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV" 2>/dev/null | cut -d= -f2)}"
WEBHOOK_URL="https://api.2notasudi.com.br/api/v1/telegram/webhook"
CHAT_ID=6682284055  # Gustavo (do PROMPT.json)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "dummy" ]; then
  echo "❌ TELEGRAM_BOT_TOKEN vazio em $ENV"
  echo "   Bot validado E2E 20/20 (2026-07-01) — token guardado no VPS."
  echo "   Para testar localmente, faça ssh root@100.99.172.84 'grep TOKEN /home/node/cartorio/.env'"
  exit 2
fi

echo "=== Bot info ==="
curl -sS -m 5 "https://api.telegram.org/bot${TOKEN}/getMe" | jq -r '.result | "Bot: @\(.username) | id=\(.id) | nome=\(.first_name)"' 2>/dev/null

echo
echo "=== Webhook info ==="
curl -sS -m 5 "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | jq -r '.result | "url=\(.url) pending=\(.pending_update_count) last_error=\(.last_error_message // "none")"' 2>/dev/null

echo
echo "=== Ping via webhook (simulado /start) ==="
START=$(date +%s%N)
RESP=$(curl -sS -m 30 -w '\n__HTTP__%{http_code}__TIME__%{time_total}' \
  -H 'Content-Type: application/json' \
  -X POST "$WEBHOOK_URL" \
  -d "{\"update_id\":999999,\"message\":{\"message_id\":1,\"from\":{\"id\":${CHAT_ID},\"first_name\":\"Gustavo\"},\"chat\":{\"id\":${CHAT_ID},\"type\":\"private\"},\"date\":$(date +%s),\"text\":\"/start\"}}" 2>&1)
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))

echo "Latência total: ${ELAPSED_MS}ms"
echo "Resposta (raw): ${RESP:0:200}..."
echo
echo "Para chat real, abra Telegram → @test_cartorio_bot → /start"
echo "Logs produção: ssh root@100.99.172.84 'docker service logs cartorio_api --tail 50 | grep telegram'"