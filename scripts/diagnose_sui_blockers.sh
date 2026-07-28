#!/usr/bin/env bash
# diagnose_sui_blockers.sh — Diagnostic helper para SUI blockers (B1-B5).
#
# Agent-doable: este script roda no Mac ou VPS sem intervencao humana.
# Detecta estado atual de cada SUI blocker e emite relatorio JSON estruturado
# que Gustavo pode usar para priorizar.
#
# NAO modifica nada. Apenas le estado.
#
# Usage:
#   bash scripts/diagnose_sui_blockers.sh
#   bash scripts/diagnose_sui_blockers.sh > artifacts/diagnostics/sui_$(date +%Y%m%d_%H%M%S).json

set -uo pipefail

JSON_OUT="${1:-/dev/stdout}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emit() {
  local blocker_id="$1"
  local status="$2"   # "ok" | "blocked_sui" | "blocked_review" | "not_applicable"
  local detail="$3"
  local action="$4"
  # JSON-escape: substitui " por \" e remove quebras de linha
  detail=$(printf '%s' "$detail" | sed 's/"/\\"/g' | tr -d '\n')
  action=$(printf '%s' "$action" | sed 's/"/\\"/g' | tr -d '\n')
  printf '{"blocker":"%s","status":"%s","detail":"%s","action":"%s"}\n' \
    "$blocker_id" "$status" "$detail" "$action"
}

# === B1 — Audit 0028 + legacy sign-off LGPD ===
B1_STATUS="unknown"
B1_DETAIL="unknown"
B1_ACTION="Run: cd backend && uv run alembic current | grep 0028 ; psql \$DATABASE_URL -c \"SELECT 1 FROM audit_log LIMIT 1\""
# Check se migration 0028 existe na arvore
if [[ -d "/Users/gustavoalmeida/Projetos/Cartorio/backend/alembic/versions" ]]; then
  MIGRATION_0028=$(ls /Users/gustavoalmeida/Projetos/Cartorio/backend/alembic/versions/ 2>/dev/null | grep -i "0028\|legacy" | head -1)
  if [[ -n "$MIGRATION_0028" ]]; then
    B1_STATUS="blocked_review"
    B1_DETAIL="Migration 0028 existe no repo: $MIGRATION_0028"
  else
    B1_STATUS="ok"
    B1_DETAIL="Nenhuma migration 0028 encontrada — pode estar aplicada ou nao criada"
  fi
fi

# === B2 — WhatsApp QR connection state ===
B2_STATUS="unknown"
B2_DETAIL="unknown"
B2_ACTION="Acessar whatsapp.2notasudi.com.br/manager ou Evolution API dashboard"
# Check se consegue alcancar o endpoint Evolution
if curl -sS -m 4 -o /dev/null -w "%{http_code}" "https://api.2notasudi.com.br/api/v1/health/radar" 2>/dev/null | grep -q "200\|401"; then
  EVOLUTION_STATE=$(curl -sS -m 8 "https://api.2notasudi.com.br/api/v1/health/radar" 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('evolution', 'unknown'))" 2>/dev/null || echo "unknown")
  B2_DETAIL="Evolution radar: $EVOLUTION_STATE (≠ sessão WA conectada — L260)"
  if [[ "$EVOLUTION_STATE" == "online" ]]; then
    B2_STATUS="blocked_sui"
  else
    B2_STATUS="not_applicable"
  fi
else
  B2_STATUS="unknown"
  B2_DETAIL="Radar endpoint nao acessivel (VPS offline ou auth required)"
fi

# === B3 — Secrets rotation status ===
B3_STATUS="blocked_sui"
B3_DETAIL="Checar timestamps de .env files vs politica 90d"
B3_ACTION="NUNCA rotacionar sob pressao (Lesson 2026-06-24)"
if [[ -f "$HOME/.hermes/profiles/cartorio/.env" ]]; then
  ENV_AGE_DAYS=$(( ( $(date +%s) - $(stat -f %m "$HOME/.hermes/profiles/cartorio/.env" 2>/dev/null || stat -c %Y "$HOME/.hermes/profiles/cartorio/.env" 2>/dev/null || echo 0) ) / 86400 ))
  B3_DETAIL=".env age: ${ENV_AGE_DAYS} days (politica: rotacionar se > 90d)"
fi

# === B4 — MCP endpoint config ===
B4_STATUS="unknown"
B4_DETAIL="unknown"
B4_ACTION="Edit ~/.hermes/profiles/cartorio/config.yaml linha 335"
if [[ -f "$HOME/.hermes/profiles/cartorio/config.yaml" ]]; then
  MCP_URL=$(grep -A1 "cartorio:" "$HOME/.hermes/profiles/cartorio/config.yaml" | grep "url:" | head -1 | awk '{print $2}')
  if [[ -n "$MCP_URL" ]]; then
    # Testar URL publica (esperado: 404 se errado)
    HTTP_CODE=$(curl -sS -m 5 -o /dev/null -w "%{http_code}" "$MCP_URL/tools/list" 2>/dev/null || echo "error")
    if [[ "$HTTP_CODE" == "404" || "$HTTP_CODE" == "error" ]]; then
      B4_STATUS="blocked_sui"
      B4_DETAIL="MCP URL $MCP_URL -> HTTP $HTTP_CODE (esperado: localhost:8000/mcp)"
    else
      B4_STATUS="ok"
      B4_DETAIL="MCP URL $MCP_URL -> HTTP $HTTP_CODE"
    fi
  fi
fi

# === B5 — Felipe visual confirmation ===
B5_STATUS="not_applicable"
B5_DETAIL="Requer iPhone fisico do Felipe — agent nao pode confirmar"
B5_ACTION="Felipe: rodar 7 mensagens de prompts/IMENSAGER_P0_IDENTITY_LEAK_INVESTIGATION.md §9"

# === Emit JSON ===
{
  echo "{"
  echo "  \"timestamp\": \"$TIMESTAMP\","
  echo "  \"hostname\": \"$(hostname)\","
  echo "  \"blockers\": ["
  emit "B1" "$B1_STATUS" "$B1_DETAIL" "$B1_ACTION" | sed 's/^/    /; s/$/,/'
  emit "B2" "$B2_STATUS" "$B2_DETAIL" "$B2_ACTION" | sed 's/^/    /; s/$/,/'
  emit "B3" "$B3_STATUS" "$B3_DETAIL" "$B3_ACTION" | sed 's/^/    /; s/$/,/'
  emit "B4" "$B4_STATUS" "$B4_DETAIL" "$B4_ACTION" | sed 's/^/    /; s/$/,/'
  emit "B5" "$B5_STATUS" "$B5_DETAIL" "$B5_ACTION" | sed 's/^/    /'
  echo "  ]"
  echo "}"
} > "$JSON_OUT"

if [[ "$JSON_OUT" == "/dev/stdout" ]]; then
  cat "$JSON_OUT"
else
  echo "[diagnose_sui_blockers] Report saved to: $JSON_OUT"
  cat "$JSON_OUT"
fi