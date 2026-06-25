#!/usr/bin/env bash
# check_ssl.sh — Verifica SSL/TLS de todos os domínios
# Uso: ./check_ssl.sh [--days 30]
#
# Verifica certificado Let's Encrypt para cada domínio

set -eo pipefail

WARN_DAYS="${2:-30}"
RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"

DOMAINS=(
    "api.2notasudi.com.br"
    "agent.2notasudi.com.br"
    "chat.2notasudi.com.br"
    "supbase.2notasudi.com.br"
    "easypanel.2notasudi.com.br"
    "whatsapp.2notasudi.com.br"
    "flow.2notasudi.com.br"
)

echo "🔒 SSL Certificate Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for domain in "${DOMAINS[@]}"; do
    expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    if [[ -z "$expiry" ]]; then
        printf "${RED}❌${NC} %-40s No certificate\n" "$domain"
        continue
    fi

    expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$expiry" +%s 2>/dev/null)
    now_epoch=$(date +%s)
    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if [[ $days_left -lt $WARN_DAYS ]]; then
        printf "${YELLOW}⚠️${NC} %-40s %d days left\n" "$domain" "$days_left"
    else
        printf "${GREEN}✅${NC} %-40s %d days left\n" "$domain" "$days_left"
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SSL check complete"
