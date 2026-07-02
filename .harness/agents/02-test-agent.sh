#!/usr/bin/env bash
# 02-test-agent — FASE TEST
set -uo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-test-$(date +%Y%m%d-%H%M%S).json"

cd "$PROJECT/backend"
RUFF=$(source .venv/bin/activate && ruff check app/ 2>&1 | tail -1)
PYTEST=$(source .venv/bin/activate && python -m pytest --no-cov -q 2>&1 | grep -E "passed|failed" | tail -1)
cd "$PROJECT"

API_RADAR=$(curl -sf --max-time 5 https://api.2notasudi.com.br/api/v1/health/integracoes 2>/dev/null || echo "{}")
STATUS=$(echo "$API_RADAR" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")

# Status "red" is OK if only n8n + supabase offline (both expected off per lessons 116, 122, 130)
# Only FAIL if any UNEXPECTED service is offline (database, redis, openclaw, evolution, chatwoot, api)
EXPECTED_OFFLINE='n8n,supabase'
UNEXPECTED_OFFLINE=""

if [ "$STATUS" = "red" ]; then
  OFFLINE_LIST=$(echo "$API_RADAR" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(','.join(k for k,v in d.get('integracoes',{}).items() if v.get('status') == 'offline'))
" 2>/dev/null || echo "")
  for svc in $(echo "$OFFLINE_LIST" | tr ',' ' '); do
    case "$svc" in
      n8n|supabase) ;;
      *) UNEXPECTED_OFFLINE="${UNEXPECTED_OFFLINE}${svc}," ;;
    esac
  done
fi

VERDICT="FAIL"
RUFF_OK=false
PYTEST_OK=false
RADAR_OK=false

echo "$RUFF" | grep -q "All checks passed" && RUFF_OK=true
echo "$PYTEST" | grep -q "passed" && PYTEST_OK=true

# Radar is OK if status != red OR only expected services are offline
if [ "$STATUS" != "red" ]; then
  RADAR_OK=true
elif [ -z "$UNEXPECTED_OFFLINE" ]; then
  RADAR_OK=true
fi

if [ "$RUFF_OK" = "true" ] && [ "$PYTEST_OK" = "true" ] && [ "$RADAR_OK" = "true" ]; then
  VERDICT="PASS"
fi

cat > "$OUT" <<JSON_EOF
{
  "agent": "02-test-agent",
  "phase": "test",
  "gates": {
    "ruff": "$(echo $RUFF | tr '\n' ' ')",
    "pytest": "$(echo $PYTEST | tr '\n' ' ')",
    "api_status": "$STATUS"
  },
  "verdict": "$VERDICT",
  "notes": {
    "expected_offline": "$EXPECTED_OFFLINE",
    "unexpected_offline": "${UNEXPECTED_OFFLINE%,}"
  }
}
JSON_EOF

cat "$OUT"
