#!/usr/bin/env bash
# check_chatwoot.sh — Verifica status do Chatwoot
# Uso: ./check_chatwoot.sh
#
# Verifica: health, accounts, conversations

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"
CW_URL="https://cartorio-chatwoot.dfgdxq.easypanel.host"
API_KEY="${CHATWOOT_API_KEY:-}"

echo "💬 Chatwoot Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Health
echo "1️⃣ Health check..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "${CW_URL}/" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" ]]; then
    printf "${GREEN}✅${NC} Chatwoot: HTTP %s\n" "$HTTP"
else
    printf "${RED}❌${NC} Chatwoot: HTTP %s\n" "$HTTP"
fi

# 2. Accounts
if [[ -n "$API_KEY" ]]; then
    echo ""
    echo "2️⃣ Accounts..."
    ACCOUNTS=$(curl -sk -H "api_access_token: $API_KEY" "${CW_URL}/api/v1/accounts" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('payload',[])))" 2>/dev/null || echo "0")
    printf "   Accounts: %s\n" "$ACCOUNTS"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Chatwoot check complete"
