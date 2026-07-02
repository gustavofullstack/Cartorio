#!/usr/bin/env bash
# 01-analyze-agent — FASE ANALYZE
set -uo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-analyze-$(date +%Y%m%d-%H%M%S).json"
cd "$PROJECT"

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
MODIFIED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
API_URL="${API_URL:-https://api.2notasudi.com.br}"
API_STATUS="offline"
curl -sf --max-time 3 "$API_URL/health" >/dev/null 2>&1 && API_STATUS="online"
COMMIT_HEAD=$(git log -1 --pretty=%h 2>/dev/null || echo "unknown")
COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "unknown")

cd "$PROJECT/backend"
PYTEST_COUNT=$(source .venv/bin/activate 2>/dev/null && python -m pytest --collect-only -q --no-cov 2>&1 | grep -E "tests collected" | head -1 || echo "unknown")
cd "$PROJECT"

MISSING_F=$(python3 -c "import fakeredis" 2>/dev/null && echo "no" || echo "yes")
MISSING_P=$(python3 -c "import pytest_asyncio" 2>/dev/null && echo "no" || echo "yes")

cat > "$OUT" <<JSON_EOF
{
  "agent": "01-analyze-agent",
  "phase": "analyze",
  "read_only": true,
  "branch": "$BRANCH",
  "modified_files": $MODIFIED,
  "api_status": "$API_STATUS",
  "pytest_collect": "$PYTEST_COUNT",
  "commit_head": "$COMMIT_HEAD",
  "commit_msg": "$COMMIT_MSG",
  "missing_deps": {
    "fakeredis": "$MISSING_F",
    "pytest-asyncio": "$MISSING_P"
  }
}
JSON_EOF

echo "✅ 01-analyze-agent DONE → $OUT"
cat "$OUT"
