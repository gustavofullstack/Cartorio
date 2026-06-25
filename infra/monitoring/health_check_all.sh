#!/usr/bin/env bash
# Health Check Unificado — Cartório 2º Notas Uberlândia (E6.S7)
# Uso: ./health_check_all.sh [--webhook TELEGRAM_BOT_TOKEN CHAT_ID]
# Dependências: curl, jq
# Testa TODOS os 7 serviços e reporta status.
# Modo --webhook: envia alerta Telegram se algum serviço estiver DOWN.

set -euo pipefail

# Config
API_URL="https://api.2notasudi.com.br"
N8N_URL="https://cartorio-n8n.dfgdxq.easypanel.host"
EVO_URL="https://whatsapp.2notasudi.com.br"
CW_URL="https://chat.2notasudi.com.br"
OCL_URL="https://agent.2notasudi.com.br"
SUP_URL="https://supbase.2notasudi.com.br"
EP_URL="https://easypanel.2notasudi.com.br"
TIMEOUT=8

# Mapa: nome -> url -> endpoint_esperado
SERVICES=(
    "API:${API_URL}:/health:200"
    "N8N:${N8N_URL}:/healthz:200"
    "EVO:${EVO_URL}:/:200"
    "OPENCLAW:${OCL_URL}:/health:200"
    "SUPABASE:${SUP_URL}:/auth/v1/health:200"
    "EASYPANEL:${EP_URL}:/:200"
)

# Telegram webhook (opcional)
TELEGRAM_BOT_TOKEN="${1:-}"
TELEGRAM_CHAT_ID="${2:-}"

DOWN=0
UP=0
REPORT=""

for svc in "${SERVICES[@]}"; do
    IFS=':' read -r name url path expected <<< "$svc"
    
    START=$(date +%s%N)
    HTTP_CODE=$(curl -sk --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "${url}${path}" 2>/dev/null || echo "000")
    END=$(date +%s%N)
    LATENCY_MS=$(( (END - START) / 1000000 ))
    
    # Supabase retorna 401 (auth required) = OK
    if [ "$name" = "SUPABASE" ] && [ "$HTTP_CODE" = "401" ]; then
        STATUS="✅"
        UP=$((UP + 1))
    elif [ "$HTTP_CODE" = "$expected" ]; then
        STATUS="✅"
        UP=$((UP + 1))
    else
        STATUS="❌"
        DOWN=$((DOWN + 1))
    fi
    
    LINE="$STATUS $name: HTTP $HTTP_CODE (${LATENCY_MS}ms)"
    REPORT="${REPORT}${LINE}\n"
done

# Add Chatwoot via Easypanel hostname
CW_ALT="https://cartorio-chatwoot.dfgdxq.easypanel.host"
START=$(date +%s%N)
CW_CODE=$(curl -sk --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "${CW_ALT}/health" 2>/dev/null || echo "000")
END=$(date +%s%N)
CW_LATENCY=$(( (END - START) / 1000000 ))

if [ "$CW_CODE" = "200" ]; then
    STATUS="✅"
    UP=$((UP + 1))
else
    STATUS="❌"
    DOWN=$((DOWN + 1))
fi
REPORT="${REPORT}${STATUS} CHATWOOT: HTTP $CW_CODE (${CW_LATENCY}ms)\n"

# Resumo
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
TOTAL=$((UP + DOWN))

echo "=== Health Check Unificado ==="
echo "Timestamp: $TIMESTAMP"
echo "Total: $TOTAL | UP: $UP | DOWN: $DOWN"
echo ""
echo -e "$REPORT"

# Alerta Telegram se algo DOWN
if [ "$DOWN" -gt 0 ] && [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    MSG="🔴 *ALERTA Cartório Health Check*
    $DOWN/$TOTAL serviços DOWN
    $(echo -e "$REPORT" | grep '❌')"
    
    curl -sk --max-time 5 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${MSG}" \
        -d "parse_mode=Markdown" > /dev/null 2>&1
fi

exit "$DOWN"
