#!/usr/bin/env bash
# monitor_services.sh — Monitor contínuo dos serviços
# Uso: ./monitor_services.sh [--once] [--interval 60]
#
# Verifica health de todos os serviços periodicamente
# Alerta via log quando serviço fica DOWN
# LGPD: NÃO loga PII

set -eo pipefail

ONCE=false; INTERVAL=60
[[ "${1:-}" == "--once" ]] && ONCE=true
[[ "${2:-}" != "" ]] && INTERVAL="${2:-60}"

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"

declare -a SERVICES=(
    "API|https://api.2notasudi.com.br/health|200"
    "N8N|https://flow.2notasudi.com.br/healthz|200"
    "EVO|https://whatsapp.2notasudi.com.br/|200"
    "CW|https://cartorio-chatwoot.dfgdxq.easypanel.host/|200"
    "OCL|https://agent.2notasudi.com.br/health|200"
    "SUP|https://supbase.2notasudi.com.br/auth/v1/health|401"
    "EP|https://easypanel.2notasudi.com.br/|200"
)

check_all() {
    local up=0 down=0 total=${#SERVICES[@]}
    local ts=$(date '+%Y-%m-%d %H:%M:%S')

    for entry in "${SERVICES[@]}"; do
        IFS='|' read -r name url expect <<< "$entry"
        code=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "$url" 2>/dev/null || echo "000")
        if [[ "$code" == "$expect" ]]; then
            up=$((up+1))
        else
            down=$((down+1))
            printf "${RED}[${ts}] DOWN: %s (HTTP %s, expected %s)${NC}\n" "$name" "$code" "$expect"
        fi
    done

    if [[ $down -eq 0 ]]; then
        printf "${GREEN}[${ts}] ALL %d/%d UP${NC}\n" "$up" "$total"
    else
        printf "${YELLOW}[${ts}] %d/%d UP, %d DOWN${NC}\n" "$up" "$total" "$down"
    fi

    return $down
}

if $ONCE; then
    check_all
else
    echo "🔄 Monitor interval: ${INTERVAL}s (Ctrl+C to stop)"
    while true; do
        check_all || true
        sleep "$INTERVAL"
    done
fi
