#!/usr/bin/env bash
# health_check_all.sh — Health check unificado 7 serviços Cartório
# Uso: ./health_check_all.sh [--json]
# LGPD: NÃO loga PII (apenas status codes e tempos)

set -eo pipefail

JSON_MODE=false
[[ "${1:-}" == "--json" ]] && JSON_MODE=true

GREEN="\033[0;32m"; RED="\033[0;31m"; NC="\033[0m"

check() {
    local name="$1" url="$2" expect="${3:-200}"
    local code time_s status
    code=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "$url" 2>/dev/null || echo "000")
    time_s=$(curl -sk -o /dev/null -w "%{time_total}" -m 8 "$url" 2>/dev/null || echo "0")
    if [[ "$code" == "$expect" ]]; then
        status="UP"; color=$GREEN; up=$((up+1))
    else
        status="DOWN"; color=$RED; down=$((down+1))
    fi
    if $JSON_MODE; then
        [[ "$first" == "true" ]] || printf ","
        printf '{"service":"%s","status":"%s","http_code":"%s","expected":"%s","time_s":"%s"}' "$name" "$status" "$code" "$expect" "$time_s"
        first=false
    else
        printf "${color}%-5s${NC} %-4s %s (%ss)\n" "$status" "$name" "$code" "$time_s"
    fi
}

up=0; down=0; first=true

if $JSON_MODE; then
    echo '{"timestamp":"'$(date -u +%FT%TZ)'","services":['
fi

check API  "https://api.2notasudi.com.br/health"                  200
check N8N  "https://flow.2notasudi.com.br/healthz"                200
check EVO  "https://whatsapp.2notasudi.com.br/"                   200
check CW   "https://cartorio-chatwoot.dfgdxq.easypanel.host/"     200
check OCL  "https://agent.2notasudi.com.br/health"                200
check SUP  "https://supbase.2notasudi.com.br/auth/v1/health"      401
check EP   "https://easypanel.2notasudi.com.br/"                  200

total=$((up+down))

if $JSON_MODE; then
    echo '],"summary":{"up":'$up',"down":'$down',"total":'$total'}}'
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "UP: ${GREEN}%d${NC} | DOWN: ${RED}%d${NC} | TOTAL: %d\n" "$up" "$down" "$total"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

[[ $down -gt 0 ]] && exit 1 || exit 0
