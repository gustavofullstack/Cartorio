#!/usr/bin/env bash
# check_all.sh — Verificação completa de todos os serviços
# Uso: ./check_all.sh [--json]
#
# Executa todos os check scripts em sequência

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🏥 FULL SYSTEM CHECK — Cartório 2º Notas"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL=0
UP=0
DOWN=0

check() {
    local name="$1" script="$2"
    TOTAL=$((TOTAL+1))
    if [[ -f "$SCRIPT_DIR/$script" ]]; then
        echo "▶ $name"
        if bash "$SCRIPT_DIR/$script" 2>/dev/null; then
            UP=$((UP+1))
        else
            DOWN=$((DOWN+1))
        fi
        echo ""
    else
        printf "  ⚠️  Script %s not found\n" "$script"
    fi
}

check "Health Check (7 services)" "health_check_all.sh"
check "Dependencies" "check_deps.sh"
check ".env Completeness" "check_env.sh"
check "SSL Certificates" "check_ssl.sh"
check "Docker Services" "check_docker.sh"
check "N8N Workflows" "validate_n8n_workflows.sh"
check "Telegram Bot" "check_telegram.sh"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "✅ UP: %d | ❌ DOWN: %d | 📁 TOTAL: %d\n" "$UP" "$DOWN" "$TOTAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $DOWN -gt 0 ]] && exit 1 || exit 0
