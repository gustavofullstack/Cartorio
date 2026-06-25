#!/usr/bin/env bash
# check_telegram.sh — Verifica status do Telegram Bot
# Uso: ./check_telegram.sh
#
# Verifica: bot info, webhook, updates

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q}"
TG_URL="https://api.telegram.org/bot${BOT_TOKEN}"

echo "🤖 Telegram Bot Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Bot info
echo "1️⃣ Bot info..."
INFO=$(curl -sk -m 8 "${TG_URL}/getMe" 2>/dev/null || echo "{}")
if echo "$INFO" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$INFO" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'].get('username','unknown'))" 2>/dev/null || echo "unknown")
    printf "${GREEN}✅${NC} Bot: @%s\n" "$BOT_NAME"
else
    printf "${RED}❌${NC} Bot: not responding\n"
fi

# 2. Webhook status
echo ""
echo "2️⃣ Webhook status..."
WEBHOOK=$(curl -sk -m 8 "${TG_URL}/getWebhookInfo" 2>/dev/null || echo "{}")
if echo "$WEBHOOK" | grep -q '"url":""'; then
    printf "${YELLOW}⚠️${NC} No webhook configured\n"
elif echo "$WEBHOOK" | grep -q '"ok":true'; then
    WEBHOOK_URL=$(echo "$WEBHOOK" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'].get('url','unknown'))" 2>/dev/null || echo "unknown")
    printf "${GREEN}✅${NC} Webhook: %s\n" "$WEBHOOK_URL"
else
    printf "${RED}❌${NC} Webhook: error\n"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Telegram check complete"
