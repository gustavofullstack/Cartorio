#!/usr/bin/env bash
# N8N Workflow Health Check — Cartório 2º Notas Uberlândia (B12)
# Uso: ./check_all_workflows.sh [--verbose]
# Dependências: curl, jq
# Lê N8N_API_KEY de .env ou argumento

set -euo pipefail

N8N_URL="${N8N_URL:-https://cartorio-n8n.dfgdxq.easypanel.host}"
N8N_API_KEY="${N8N_API_KEY:-}"

if [ -z "$N8N_API_KEY" ] && [ -f "../../backend/.env" ]; then
    N8N_API_KEY=$(grep "^N8N_API_KEY=" ../../backend/.env | cut -d= -f2-)
fi

if [ -z "$N8N_API_KEY" ]; then
    echo "ERRO: N8N_API_KEY nao encontrada. Defina via env ou ./backend/.env"
    exit 1
fi

VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

REPORT=$(mktemp)
trap 'rm -f "$REPORT"' EXIT

echo "=== N8N Workflow Health Check ==="
echo "URL: $N8N_URL"
echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# Lista todos workflows
WORKFLOWS=$(curl -sk --max-time 15 \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "$N8N_URL/api/v1/workflows?limit=100" 2>/dev/null)

if [ -z "$WORKFLOWS" ]; then
    echo "ERRO: Nao foi possivel conectar ao N8N API"
    exit 2
fi

echo "$WORKFLOWS" | jq -c '.data[]' 2>/dev/null | while read -r wf; do
    ID=$(echo "$wf" | jq -r '.id')
    NAME=$(echo "$wf" | jq -r '.name')
    ACTIVE_STATUS=$(echo "$wf" | jq -r '.active')
    
    if [ "$ACTIVE_STATUS" = "true" ]; then
        STATUS="✅"
        echo "active" >> "$REPORT"
    else
        STATUS="❌"
        echo "inactive" >> "$REPORT"
    fi
    
    # Verifica se tem executions com erro recentes
    RECENT_EXECS=$(curl -sk --max-time 10 \
        -H "X-N8N-API-KEY: $N8N_API_KEY" \
        "$N8N_URL/api/v1/workflows/$ID/executions?limit=5&status=error" 2>/dev/null | \
        jq '[.data[] | select(.finished and (.status == "error"))] | length' 2>/dev/null || echo "0")
    
    if [ "$RECENT_EXECS" -gt 0 ] && [ "$ACTIVE_STATUS" = "true" ]; then
        echo "error" >> "$REPORT"
        ERROR_FLAG=" ⚠️ $RECENT_EXECS erros recentes"
    else
        ERROR_FLAG=""
    fi
    
    echo "$STATUS $NAME (${ID})${ERROR_FLAG}"
done

echo ""
echo "=== Resumo ==="
TOTAL=$(wc -l < "$REPORT" 2>/dev/null || echo 0)
ACTIVE=$(grep -c "active" "$REPORT" 2>/dev/null || echo 0)
ERRORS=$(grep -c "error" "$REPORT" 2>/dev/null || echo 0)
INACTIVE=$((TOTAL - ACTIVE))
echo "Total: $TOTAL | Ativos: $ACTIVE | Inativos: $INACTIVE | Com erros: $ERRORS"
