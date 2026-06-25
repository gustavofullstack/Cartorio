#!/usr/bin/env bash
# check_evolution.sh — Verifica status da Evolution API
# Uso: ./check_evolution.sh
#
# Verifica: health, instance status, webhook config

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
EVO_URL="https://whatsapp.2notasudi.com.br"
API_KEY="${EVOLUTION_API_KEY:-}"

echo "📱 Evolution API Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Health
echo "1️⃣ Health check..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "${EVO_URL}/" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" ]]; then
    printf "${GREEN}✅${NC} Evolution: HTTP %s\n" "$HTTP"
else
    printf "${RED}❌${NC} Evolution: HTTP %s\n" "$HTTP"
fi

# 2. Instance status
if [[ -n "$API_KEY" ]]; then
    echo ""
    echo "2️⃣ Instance status..."
    INSTANCES=$(curl -sk -H "apikey: $API_KEY" "${EVO_URL}/instance/fetchInstances" 2>/dev/null || echo "[]")
    if echo "$INSTANCES" | grep -q "cartorio-2notas"; then
        STATE=$(echo "$INSTANCES" | python3 -c "import json,sys; d=json.load(sys.stdin); insts=[i for i in d if 'cartorio' in i.get('name','')]; print(insts[0].get('state','unknown') if insts else 'not found')" 2>/dev/null || echo "unknown")
        if [[ "$STATE" == "open" ]]; then
            printf "${GREEN}✅${NC} Instance cartorio-2notas: %s\n" "$STATE"
        else
            printf "${YELLOW}⚠️${NC} Instance cartorio-2notas: %s (needs QR scan)\n" "$STATE"
        fi
    else
        printf "${YELLOW}⚠️${NC} Instance cartorio-2notas not found\n"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Evolution API check complete"
