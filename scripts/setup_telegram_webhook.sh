#!/bin/bash
set -euo pipefail

TOKEN="${TELEGRAM_BOT_TOKEN:-}"

if [ -z "$TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN environment variable is not set."
    echo "Usage: TELEGRAM_BOT_TOKEN='your_token' ./setup_telegram_webhook.sh"
    exit 1
fi

WEBHOOK_URL="https://api.2notasudi.com.br/api/v1/telegram/webhook"
SECRET="cartorio_webhook_secret_telegram"

curl -sS -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\", \"secret_token\": \"${SECRET}\"}"

echo ""
echo "Webhook registered."
