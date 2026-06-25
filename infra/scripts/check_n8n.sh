#!/usr/bin/env bash
# check_n8n.sh — Verifica status do N8N
# Uso: ./check_n8n.sh
#
# Verifica: health, workflows, executions, credentials

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
N8N_URL="https://flow.2notasudi.com.br"
API_KEY="${N8N_API_KEY:-}"

echo "⚙️ N8N Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Health check
echo "1️⃣ Health check..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "${N8N_URL}/healthz" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" ]]; then
    printf "${GREEN}✅${NC} N8N: HTTP %s\n" "$HTTP"
else
    printf "${RED}❌${NC} N8N: HTTP %s\n" "$HTTP"
fi

# 2. Workflows count
if [[ -n "$API_KEY" ]]; then
    echo ""
    echo "2️⃣ Workflows..."
    WF_COUNT=$(curl -sk -H "X-N8N-API-KEY: $API_KEY" "${N8N_URL}/api/v1/workflows" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
    printf "   Active workflows: %s\n" "$WF_COUNT"

    # 3. Recent executions
    echo ""
    echo "3️⃣ Recent executions..."
    EXEC_COUNT=$(curl -sk -H "X-N8N-API-KEY: $API_KEY" "${N8N_URL}/api/v1/executions?limit=10" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
    printf "   Last 10 executions: %s\n" "$EXEC_COUNT"
else
    echo ""
    echo "2️⃣ Workflows..."
    printf "${YELLOW}⚠️${NC} N8N_API_KEY not set — skipping workflow count\n"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ N8N check complete"
