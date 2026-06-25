#!/usr/bin/env bash
# check_api_keys.sh — Verifica se API keys estão configuradas
# Uso: ./check_api_keys.sh
#
# NÃO expõe valores — apenas verifica existência

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"

echo "🔑 API Keys Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_key() {
    local name="$1" var="$2"
    if [[ -n "${!var:-}" ]]; then
        printf "${GREEN}✅${NC} %-25s configured\n" "$name"
    else
        printf "${RED}❌${NC} %-25s NOT SET\n" "$name"
    fi
}

check_key "Minimax API" "MINIMAX_API_KEY"
check_key "Telegram Bot" "TELEGRAM_BOT_TOKEN"
check_key "Jules API" "JULES_API_KEY"
check_key "Render API" "RENDER_API_KEY"
check_key "Linear API" "LINEAR_API_KEY"
check_key "OpenCode-Go" "OPENCODE_GO_API_KEY"
check_key "N8N API" "N8N_API_KEY"
check_key "Chatwoot API" "CHATWOOT_API_KEY"
check_key "Evolution API" "EVOLUTION_API_KEY"
check_key "Cartorio API" "CARTORIO_API_KEY"
check_key "Easypanel" "EASYPANEL_API_KEY"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ API keys check complete"
