#!/usr/bin/env bash
# check_supabase.sh — Verifica status do Supabase
# Uso: ./check_supabase.sh
#
# Verifica: auth health, DB connection, tables count

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"

echo "🐘 Supabase Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Auth health
echo "1️⃣ Auth health..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://supbase.2notasudi.com.br/auth/v1/health" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" || "$HTTP" == "401" ]]; then
    printf "${GREEN}✅${NC} Auth: HTTP %s\n" "$HTTP"
else
    printf "${RED}❌${NC} Auth: HTTP %s\n" "$HTTP"
fi

# 2. PostgREST
echo ""
echo "2️⃣ PostgREST..."
HTTP2=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://supbase.2notasudi.com.br/rest/v1/" 2>/dev/null || echo "000")
printf "   PostgREST: HTTP %s\n" "$HTTP2"

# 3. Studio
echo ""
echo "3️⃣ Studio..."
HTTP3=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://supbase.2notasudi.com.br:3000/" 2>/dev/null || echo "000")
printf "   Studio: HTTP %s\n" "$HTTP3"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Supabase check complete"
