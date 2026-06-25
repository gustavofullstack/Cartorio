#!/usr/bin/env bash
# check_env.sh — Verifica se .env está completo para cada serviço
# Uso: ./check_env.sh [--fix]
#
# LGPD: NÃO expõe valores das chaves, apenas verifica existência

set -eo pipefail

FIX=false
[[ "${1:-}" == "--fix" ]] && FIX=true

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"

echo "🔍 Checking .env files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Required env vars per service
declare -A REQUIRED=(
    ["API"]="DATABASE_URL REDIS_URL AUDIT_HMAC_KEY"
    ["REDIS"]="REDIS_URL"
    ["N8N"]="N8N_API_KEY"
    ["SUPABASE"]="SUPABASE_URL SUPABASE_ANON_KEY"
    ["EVOLUTION"]="EVOLUTION_API_URL"
    ["CHATWOOT"]="CHATWOOT_API_KEY"
    ["OPENCLAW"]="OPENCODE_GO_API_KEY"
)

MISSING=0
FOUND=0

for service in API REDIS N8N SUPABASE EVOLUTION CHATWOOT OPENCLAW; do
    echo ""
    echo "📦 $service:"
    for var in ${REQUIRED[$service]}; do
        if [[ -n "${!var:-}" ]]; then
            printf "  ${GREEN}✅${NC} %s\n" "$var"
            FOUND=$((FOUND+1))
        else
            printf "  ${RED}❌${NC} %s (missing)\n" "$var"
            MISSING=$((MISSING+1))
            if $FIX; then
                printf "  ${YELLOW}⚠️  Add to .env: %s=<value>${NC}\n" "$var"
            fi
        fi
    done
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "Found: ${GREEN}%d${NC} | Missing: ${RED}%d${NC}\n" "$FOUND" "$MISSING"

[[ $MISSING -gt 0 ]] && exit 1 || exit 0
